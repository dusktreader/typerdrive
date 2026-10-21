import asyncio
import inspect
import threading
from pathlib import Path

import aiosqlite
import pytest
from typerdrive.async_tools import BlockingAsyncAdapter
from typerdrive.database.exceptions import (
    DatabaseInitError,
    DatabaseLifecycleError,
    DatabaseQueryError,
    DatabaseRollbackError,
    DatabaseTransactionError,
)
from typerdrive.database.session import DatabaseSession


def run(coro):
    return asyncio.run(coro)


class TestDatabaseSession:
    def test_async_lifecycle_creates_parent_and_uses_wal(self, tmp_path: Path):
        path = tmp_path / "nested" / "database.sqlite"
        manager = DatabaseSession(path)

        async def scenario():
            async with manager:
                assert path.parent.is_dir()
                assert manager.is_open
                assert await manager.fetch_value("PRAGMA journal_mode") == "wal"
            assert not manager.is_open

        run(scenario())

    def test_async_sql_methods_parameterize_and_fetch_rows(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                await manager.execute("CREATE TABLE item (name TEXT, count INTEGER)")
                await manager.execute("INSERT INTO item VALUES (?, ?)", ("gear", 3))
                rows = await manager.fetch_all("SELECT name, count FROM item")
                assert [tuple(row) for row in rows] == [("gear", 3)]
                assert await manager.fetch_value("SELECT count FROM item") == 3

        run(scenario())

    def test_alternate_journal_mode(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite", journal_mode="DELETE")

        async def scenario():
            async with manager:
                assert await manager.fetch_value("PRAGMA journal_mode") == "delete"

        run(scenario())

    def test_invalid_journal_mode_fails_initialization(self, tmp_path: Path):
        with pytest.raises(DatabaseInitError, match="journal mode"):
            DatabaseSession(tmp_path / "database.sqlite", journal_mode="INVALID")

    def test_query_failure_is_wrapped(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                with pytest.raises(DatabaseQueryError):
                    await manager.execute("SELECT * FROM missing_table")

        run(scenario())

    def test_transaction_commits_and_rolls_back(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                await manager.execute("CREATE TABLE item (value INTEGER)")
                async with manager.transaction():
                    await manager.execute("INSERT INTO item VALUES (1)")
                with pytest.raises(ValueError):
                    async with manager.transaction():
                        await manager.execute("INSERT INTO item VALUES (2)")
                        raise ValueError("rollback")
                rows = await manager.fetch_all("SELECT value FROM item")
                assert [tuple(row) for row in rows] == [(1,)]

        run(scenario())

    def test_async_transaction_uses_rollback_error_when_rollback_fails(self, tmp_path: Path, monkeypatch):
        async def fail_rollback(connection):
            raise OSError("rollback failed")

        monkeypatch.setattr(aiosqlite.Connection, "rollback", fail_rollback)
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                with pytest.raises(DatabaseRollbackError, match="roll back"):
                    async with manager.transaction():
                        raise ValueError("transaction failed")

        run(scenario())

    def test_async_transaction_rejects_nesting_with_lifecycle_error(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                async with manager.transaction():
                    with pytest.raises(DatabaseLifecycleError, match="Nested"):
                        async with manager.transaction():
                            pass

        run(scenario())

    def test_non_owner_waits_until_transaction_finishes(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                await manager.execute("CREATE TABLE item (value INTEGER)")
                entered = asyncio.Event()
                release = asyncio.Event()

                async def transaction_owner():
                    async with manager.transaction():
                        await manager.execute("INSERT INTO item VALUES (1)")
                        entered.set()
                        await release.wait()

                task = asyncio.create_task(transaction_owner())
                await entered.wait()
                writer = asyncio.create_task(manager.execute("INSERT INTO item VALUES (2)"))
                await asyncio.sleep(0)
                assert not writer.done()
                release.set()
                await task
                await writer
                rows = await manager.fetch_all("SELECT value FROM item ORDER BY value")
                assert [row[0] for row in rows] == [1, 2]

        run(scenario())

    def test_cancelled_transaction_rolls_back_and_closes(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            with pytest.raises(asyncio.CancelledError):
                async with manager:
                    await manager.execute("CREATE TABLE item (value INTEGER)")

                    async def cancel_transaction():
                        async with manager.transaction():
                            await manager.execute("INSERT INTO item VALUES (1)")
                            raise asyncio.CancelledError

                    await cancel_transaction()
            assert not manager.is_open
            async with manager:
                assert await manager.fetch_value("SELECT COUNT(*) FROM item") == 0

        run(scenario())

    def test_sync_lifecycle_keeps_one_connection(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")
        assert isinstance(manager._sync_adapter, BlockingAsyncAdapter)
        assert not hasattr(manager, "_async_bridge")

        with manager:
            assert manager.is_open
            manager.execute_sync("CREATE TABLE item (value INTEGER)")
            manager.execute_sync("INSERT INTO item VALUES (?)", (7,))
            assert manager.fetch_value_sync("SELECT value FROM item") == 7
        assert not manager.is_open

    def test_manager_does_not_reference_portal_implementation(self):
        source = inspect.getsource(DatabaseSession)
        assert "BlockingPortal" not in source
        assert "start_blocking_portal" not in source
        assert "_portal" not in source
        assert "_async_bridge" not in source

    def test_async_and_sync_apis_cannot_be_mixed(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                with pytest.raises(DatabaseLifecycleError, match="async"):
                    manager.fetch_value_sync("SELECT 1")

        run(scenario())

    def test_sync_calls_reject_running_event_loop(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            with pytest.raises(DatabaseLifecycleError, match="async API"):
                manager.fetch_value_sync("SELECT 1")

        run(scenario())

    def test_sync_lifecycle_rejects_running_event_loop(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            with pytest.raises(DatabaseLifecycleError, match="async with"):
                with manager:
                    pass

        run(scenario())

    def test_async_api_cannot_join_sync_lifecycle(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")
        entered = threading.Event()
        release = threading.Event()

        def sync_lifecycle():
            with manager:
                entered.set()
                release.wait()

        async def scenario():
            thread = threading.Thread(target=sync_lifecycle)
            thread.start()
            assert await asyncio.to_thread(entered.wait, 5)
            try:
                with pytest.raises(DatabaseLifecycleError, match="sync"):
                    await manager.fetch_value("SELECT 1")
            finally:
                release.set()
                await asyncio.to_thread(thread.join, 5)
            assert not thread.is_alive()

        run(scenario())

    def test_connection_failure_is_wrapped(self, tmp_path: Path, monkeypatch):
        async def fail_connect(*args, **kwargs):
            raise OSError("connection failed")

        monkeypatch.setattr("typerdrive.database.session.aiosqlite.connect", fail_connect)
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            with pytest.raises(DatabaseInitError, match="connection failed"):
                async with manager:
                    pass

        run(scenario())

    def test_close_failure_is_wrapped(self, tmp_path: Path, monkeypatch):
        original_close = aiosqlite.Connection.close

        async def close_then_fail(connection):
            await original_close(connection)
            raise OSError("close failed")

        monkeypatch.setattr(aiosqlite.Connection, "close", close_then_fail)
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            with pytest.raises(DatabaseInitError, match="close failed"):
                async with manager:
                    pass
            assert not manager.is_open

        run(scenario())

    def test_parent_directory_failure_is_wrapped(self, tmp_path: Path, monkeypatch):
        def fail_mkdir(*args, **kwargs):
            raise OSError("permission denied")

        monkeypatch.setattr("typerdrive.database.session.Path.mkdir", fail_mkdir)
        manager = DatabaseSession(tmp_path / "nested" / "database.sqlite")

        async def scenario():
            with pytest.raises(DatabaseInitError, match="permission denied"):
                async with manager:
                    pass

        run(scenario())

    def test_sync_transaction_rolls_back_on_exception(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        with manager:
            manager.execute_sync("CREATE TABLE item (value INTEGER)")
            with pytest.raises(ValueError):
                with manager.transaction_sync():
                    manager.execute_sync("INSERT INTO item VALUES (1)")
                    raise ValueError("rollback")
            assert manager.fetch_value_sync("SELECT COUNT(*) FROM item") == 0

    def test_sync_transaction_rolls_back_after_deferred_constraint_commit_failure(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        with manager:
            manager.execute_sync("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            manager.execute_sync(
                "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)"
            )
            with pytest.raises(DatabaseTransactionError, match="commit"):
                with manager.transaction_sync():
                    manager.execute_sync("INSERT INTO child VALUES (1)")
            assert manager.fetch_value_sync("SELECT COUNT(*) FROM child") == 0
            manager.execute_sync("INSERT INTO parent VALUES (1)")
            manager.execute_sync("INSERT INTO child VALUES (1)")
            assert manager.fetch_value_sync("SELECT COUNT(*) FROM child") == 1

    def test_sync_transaction_preserves_commit_and_rollback_failures(self, tmp_path: Path, monkeypatch):
        manager = DatabaseSession(tmp_path / "database.sqlite")
        original_rollback = aiosqlite.Connection.rollback

        async def fail_rollback(connection):
            raise OSError("rollback failed")

        monkeypatch.setattr(aiosqlite.Connection, "rollback", fail_rollback)
        try:
            with manager:
                manager.execute_sync("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
                manager.execute_sync(
                    "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)"
                )
                with pytest.raises(DatabaseRollbackError, match="commit.*rollback") as error:
                    with manager.transaction_sync():
                        manager.execute_sync("INSERT INTO child VALUES (1)")
                assert isinstance(error.value.__cause__, ExceptionGroup)
                commit_failure, rollback_failure = error.value.__cause__.exceptions
                assert str(commit_failure) == "FOREIGN KEY constraint failed"
                assert isinstance(rollback_failure, DatabaseRollbackError)
                assert str(rollback_failure.__cause__) == "rollback failed"
        finally:
            monkeypatch.setattr(aiosqlite.Connection, "rollback", original_rollback)

    def test_sync_transaction_isolates_cross_thread_commit(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")
        started = threading.Event()
        finished = threading.Event()

        with manager:
            manager.execute_sync("CREATE TABLE item (value INTEGER)")

            def insert_from_worker():
                started.set()
                manager.execute_sync("INSERT INTO item VALUES (2)")
                finished.set()

            with manager.transaction_sync():
                manager.execute_sync("INSERT INTO item VALUES (1)")
                worker = threading.Thread(target=insert_from_worker)
                worker.start()
                assert started.wait(5)
                assert not finished.wait(0.1)
            worker.join(5)
            assert not worker.is_alive()
            rows = manager.fetch_all_sync("SELECT value FROM item ORDER BY value")
            assert [tuple(row) for row in rows] == [(1,), (2,)]

    def test_sync_transaction_isolates_cross_thread_rollback(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")
        started = threading.Event()
        finished = threading.Event()

        with manager:
            manager.execute_sync("CREATE TABLE item (value INTEGER)")

            def insert_from_worker():
                started.set()
                manager.execute_sync("INSERT INTO item VALUES (2)")
                finished.set()

            with pytest.raises(ValueError, match="rollback"):
                with manager.transaction_sync():
                    manager.execute_sync("INSERT INTO item VALUES (1)")
                    worker = threading.Thread(target=insert_from_worker)
                    worker.start()
                    assert started.wait(5)
                    assert not finished.wait(0.1)
                    raise ValueError("rollback")
            worker.join(5)
            assert not worker.is_alive()
            rows = manager.fetch_all_sync("SELECT value FROM item ORDER BY value")
            assert [tuple(row) for row in rows] == [(2,)]

    def test_sync_transaction_rejects_nesting(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")

        with manager:
            with manager.transaction_sync():
                with pytest.raises(DatabaseLifecycleError, match="Nested"):
                    with manager.transaction_sync():
                        pass

    def test_cross_thread_transaction_waits_until_commit(self, tmp_path: Path):
        manager = DatabaseSession(tmp_path / "database.sqlite")
        started = threading.Event()
        finished = threading.Event()

        with manager:
            manager.execute_sync("CREATE TABLE item (value INTEGER)")

            def insert_from_worker():
                started.set()
                with manager.transaction_sync():
                    manager.execute_sync("INSERT INTO item VALUES (2)")
                finished.set()

            with manager.transaction_sync():
                manager.execute_sync("INSERT INTO item VALUES (1)")
                worker = threading.Thread(target=insert_from_worker)
                worker.start()
                assert started.wait(5)
                assert not finished.wait(0.1)
            worker.join(5)
            assert not worker.is_alive()
            assert finished.is_set()
            rows = manager.fetch_all_sync("SELECT value FROM item ORDER BY value")
            assert [tuple(row) for row in rows] == [(1,), (2,)]

    def test_manager_exposes_configured_path(self, tmp_path: Path):
        path = tmp_path / "configured.sqlite"
        assert DatabaseSession(path).database_path == path
