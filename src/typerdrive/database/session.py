import asyncio
import sqlite3
import threading
from collections.abc import AsyncIterator, Iterable, Sequence
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any

import aiosqlite

from typerdrive.async_tools import BlockingAsyncAdapter, current_sync_adapter, ensure_sync_context
from typerdrive.config import get_typerdrive_config
from typerdrive.database.exceptions import (
    DatabaseInitError,
    DatabaseLifecycleError,
    DatabaseQueryError,
    DatabaseRollbackError,
    DatabaseTransactionError,
)


class DatabaseSession:
    def __init__(self, database_path: Path | str | None = None, journal_mode: str = "WAL"):
        self.database_path = Path(database_path) if database_path is not None else get_typerdrive_config().database_path
        self.journal_mode = journal_mode.upper()
        if self.journal_mode not in {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}:
            raise DatabaseInitError(f"Unsupported SQLite journal mode: {journal_mode}")
        self.connection: aiosqlite.Connection | None = None
        self._mode: str | None = None
        self._operation_lock = asyncio.Lock()
        self._transaction_owner: asyncio.Task[Any] | None = None
        self._sync_operation_lock = threading.RLock()
        self._sync_transaction_active = False
        self._sync_adapter = BlockingAsyncAdapter(self._sync_lifecycle)

    @property
    def is_open(self) -> bool:
        return self.connection is not None

    async def __aenter__(self):
        if self._mode is not None:
            raise DatabaseLifecycleError("Database session lifecycle is already active")
        self._mode = "async"
        try:
            await self._open()
        except BaseException:
            self._mode = None
            raise
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._close()

    def __enter__(self):
        if self._mode is not None:
            raise DatabaseLifecycleError("Database session lifecycle is already active")
        ensure_sync_context(
            lambda: DatabaseLifecycleError(
                "Synchronous database lifecycles cannot run inside an event loop; use async with"
            )
        )
        self._mode = "sync"
        try:
            self._sync_adapter.__enter__()
        except BaseException:
            self._mode = None
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self._sync_adapter.__exit__(exc_type, exc_value, traceback)
        finally:
            self._mode = None

    @asynccontextmanager
    async def _sync_lifecycle(self) -> AsyncIterator["DatabaseSession"]:
        await self._open()
        try:
            yield self
        finally:
            await self._close()

    async def _open(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = await aiosqlite.connect(self.database_path, timeout=30)
            self.connection.row_factory = sqlite3.Row
            await self.connection.execute("PRAGMA busy_timeout=30000")
            await self._configure_journal_mode()
            await self.connection.execute("PRAGMA foreign_keys=ON")
        except BaseException as error:
            await self._close_connection()
            if isinstance(error, DatabaseInitError):
                raise
            DatabaseInitError.raise_from(f"Failed to initialize database at {self.database_path}", error)

    async def _configure_journal_mode(self) -> None:
        connection = DatabaseInitError.enforce_defined(self.connection, "Database connection is not open")
        deadline = asyncio.get_running_loop().time() + 30
        while True:
            try:
                cursor = await connection.execute(f"PRAGMA journal_mode={self.journal_mode}")
                row = DatabaseInitError.enforce_defined(
                    await cursor.fetchone(),
                    "SQLite returned no journal mode",
                )
                await cursor.close()
                actual_mode = str(row[0]).upper()
                DatabaseInitError.require_condition(
                    actual_mode == self.journal_mode,
                    f"SQLite did not apply requested journal mode {self.journal_mode}; actual mode is {actual_mode}",
                )
                return
            except sqlite3.OperationalError as error:
                if "locked" not in str(error).lower() or asyncio.get_running_loop().time() >= deadline:
                    raise
                await asyncio.sleep(0.05)

    async def _close(self) -> None:
        try:
            if self.connection is not None:
                await self._close_connection()
        finally:
            self._mode = None

    async def _close_connection(self) -> None:
        if self.connection is not None:
            connection = self.connection
            self.connection = None
            with DatabaseInitError.handle_errors(f"Failed to close database at {self.database_path}"):
                await asyncio.shield(connection.close())

    def _check_async(self) -> aiosqlite.Connection:
        if self._mode == "sync":
            DatabaseLifecycleError.require_condition(
                current_sync_adapter() is self._sync_adapter,
                "Database session uses its sync API for this lifecycle",
            )
        elif self._mode != "async":
            raise DatabaseLifecycleError("Enter the database session with 'async with' before using its async API")
        return DatabaseLifecycleError.enforce_defined(self.connection, "Database session connection is not open")

    def _check_sync(self) -> None:
        ensure_sync_context(
            lambda: DatabaseLifecycleError("Sync database wrappers cannot run inside an event loop; use the async API")
        )
        DatabaseLifecycleError.require_condition(
            self._mode != "async",
            "Database session uses its async API for this lifecycle",
        )
        DatabaseLifecycleError.require_condition(
            self._mode == "sync" and self.connection is not None,
            "Enter the database session with 'with' before using its sync API",
        )

    @asynccontextmanager
    async def _operation(self) -> AsyncIterator[aiosqlite.Connection]:
        connection = self._check_async()
        task = asyncio.current_task()
        if self._transaction_owner is task or current_sync_adapter() is self._sync_adapter:
            yield connection
        else:
            async with self._operation_lock:
                yield connection

    async def execute(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> int:
        try:
            async with self._operation() as connection:
                cursor = await connection.execute(sql, parameters)
                rowcount = cursor.rowcount
                await cursor.close()
                if self._transaction_owner is not asyncio.current_task() and not self._sync_transaction_active:
                    await connection.commit()
                return rowcount
        except DatabaseLifecycleError:
            raise
        except Exception as error:
            raise DatabaseQueryError(f"Failed to execute database query: {error}") from error

    async def fetch_one(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> sqlite3.Row | None:
        try:
            async with self._operation() as connection:
                cursor = await connection.execute(sql, parameters)
                row = await cursor.fetchone()
                await cursor.close()
                return row
        except DatabaseLifecycleError:
            raise
        except Exception as error:
            raise DatabaseQueryError(f"Failed to fetch database row: {error}") from error

    async def fetch_all(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> list[sqlite3.Row]:
        try:
            async with self._operation() as connection:
                cursor = await connection.execute(sql, parameters)
                rows = list(await cursor.fetchall())
                await cursor.close()
                return rows
        except DatabaseLifecycleError:
            raise
        except Exception as error:
            raise DatabaseQueryError(f"Failed to fetch database rows: {error}") from error

    async def fetch_value(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> Any:
        row = await self.fetch_one(sql, parameters)
        return None if row is None else row[0]

    async def _rollback(self, connection: aiosqlite.Connection) -> None:
        with DatabaseRollbackError.handle_errors("Failed to roll back database transaction"):
            await asyncio.shield(connection.rollback())

    @asynccontextmanager
    async def transaction(self, immediate: bool = False) -> AsyncIterator["DatabaseSession"]:
        connection = self._check_async()
        DatabaseLifecycleError.require_condition(
            self._transaction_owner is not asyncio.current_task(),
            "Nested database transactions are not supported",
        )
        await self._operation_lock.acquire()
        self._transaction_owner = asyncio.current_task()
        try:
            await connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield self
            await connection.commit()
        except BaseException as error:
            await self._rollback(connection)
            if isinstance(error, sqlite3.Error):
                DatabaseTransactionError.raise_from("Database transaction failed", error)
            raise
        finally:
            self._transaction_owner = None
            self._operation_lock.release()

    def execute_sync(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> int:
        self._check_sync()
        with self._sync_operation_lock:
            self._check_sync()
            return self._sync_adapter.run(self.execute, sql, parameters)

    def fetch_one_sync(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> sqlite3.Row | None:
        self._check_sync()
        with self._sync_operation_lock:
            self._check_sync()
            return self._sync_adapter.run(self.fetch_one, sql, parameters)

    def fetch_all_sync(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> list[sqlite3.Row]:
        self._check_sync()
        with self._sync_operation_lock:
            self._check_sync()
            return self._sync_adapter.run(self.fetch_all, sql, parameters)

    def fetch_value_sync(self, sql: str, parameters: Sequence[Any] | Iterable[Any] = ()) -> Any:
        self._check_sync()
        with self._sync_operation_lock:
            self._check_sync()
            return self._sync_adapter.run(self.fetch_value, sql, parameters)

    @contextmanager
    def transaction_sync(self):
        self._check_sync()
        self._sync_operation_lock.acquire()
        try:
            self._check_sync()
            DatabaseLifecycleError.require_condition(
                not self._sync_transaction_active,
                "Nested database transactions are not supported",
            )
            self._sync_transaction_active = True
            try:
                self._sync_adapter.run(self._begin_sync_transaction)
                try:
                    yield self
                except BaseException:
                    self._sync_adapter.run(self._finish_sync_transaction, commit=False)
                    raise
                else:
                    self._sync_adapter.run(self._finish_sync_transaction, commit=True)
            finally:
                self._sync_transaction_active = False
        finally:
            self._sync_operation_lock.release()

    async def _begin_sync_transaction(self) -> None:
        connection = self._check_async()
        async with DatabaseTransactionError.handle_errors_async("Failed to begin database transaction"):
            await connection.execute("BEGIN")

    async def _finish_sync_transaction(self, commit: bool) -> None:
        connection = self._check_async()
        if commit:
            try:
                await connection.commit()
            except Exception as commit_error:
                try:
                    await self._rollback(connection)
                except DatabaseRollbackError as rollback_error:
                    failures = ExceptionGroup(
                        "Database transaction commit and rollback failed",
                        [commit_error, rollback_error],
                    )
                    raise DatabaseRollbackError(
                        f"Failed to commit database transaction: {commit_error}; rollback also failed"
                    ) from failures
                raise DatabaseTransactionError(
                    f"Failed to commit database transaction: {commit_error}"
                ) from commit_error
        else:
            await self._rollback(connection)
