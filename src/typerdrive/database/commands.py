import sqlite3
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

import typer

from typerdrive.async_tools import run_async as run_async_helper
from typerdrive.config import get_typerdrive_config
from typerdrive.database.exceptions import DatabaseError, DatabaseLifecycleError, DatabaseManagementError
from typerdrive.database.manager import DatabaseManager
from typerdrive.database.migrations import MigrationRegistry
from typerdrive.handle_errors import handle_errors


T = TypeVar("T")


def _run_cli_async(async_callable: Callable[..., Awaitable[T]], *args: Any) -> T:
    return run_async_helper(
        async_callable,
        *args,
        running_loop_error=lambda: DatabaseLifecycleError(
            "Synchronous database commands cannot run inside an event loop; invoke the command synchronously"
        ),
    )


def database_path() -> Path:
    return get_typerdrive_config().database_path


def path() -> None:
    typer.echo(database_path())


@handle_errors("Failed to inspect database", handle_exc_class=DatabaseError)
def inspect() -> None:
    db_path = database_path()
    if not db_path.exists():
        typer.echo(f"Database does not exist: {db_path}")
        return
    try:
        connection = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            sqlite_version = connection.execute("SELECT sqlite_version()").fetchone()[0]
            schema_version = connection.execute("PRAGMA schema_version").fetchone()[0]
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise DatabaseManagementError(f"Failed to inspect database metadata: {error}") from error
    typer.echo(f"Database: {db_path}")
    typer.echo("Exists: yes")
    typer.echo(f"SQLite version: {sqlite_version}")
    typer.echo(f"Schema version: {schema_version}")
    typer.echo(f"Journal mode: {journal_mode}")


@handle_errors("Failed to read database migration status", handle_exc_class=DatabaseError)
def status(registry: MigrationRegistry) -> None:
    applied, pending = _run_cli_async(registry.get_status, database_path())
    for migration in applied:
        typer.echo(f"applied {migration.migration_id}")
    for migration in pending:
        typer.echo(f"pending {migration.migration_id}")
    if not applied and not pending:
        typer.echo("All registered migrations are applied")


@handle_errors("Failed to set up database", handle_exc_class=DatabaseError)
def setup() -> None:
    db_path = database_path()
    if db_path.exists():
        typer.echo(f"Database is already set up: {db_path}")
        return

    async def initialize() -> None:
        async with DatabaseManager(db_path).create_session():
            pass

    try:
        _run_cli_async(initialize)
    except DatabaseError:
        raise
    except Exception as error:
        raise DatabaseManagementError(f"Failed to set up database at {db_path}: {error}") from error
    typer.echo(f"Database set up: {db_path}")


@handle_errors("Failed to apply database migrations", handle_exc_class=DatabaseError)
def migrate(registry: MigrationRegistry) -> None:
    db_path = database_path()
    if not db_path.exists():
        raise DatabaseManagementError(
            f"Database does not exist at {db_path}; run 'db setup' or invoke an attached command first"
        )

    async def apply_migrations() -> None:
        async with DatabaseManager(db_path).create_session() as session:
            await registry.apply(session)

    try:
        _run_cli_async(apply_migrations)
    except DatabaseError:
        raise
    except Exception as error:
        raise DatabaseManagementError(f"Failed to apply database migrations: {error}") from error
    typer.echo(f"Database migrations applied: {db_path}")


@handle_errors("Failed to reset database", handle_exc_class=DatabaseError)
def reset(registry: MigrationRegistry) -> None:
    db_path = database_path()
    typer.confirm("Reset the database and delete all application data?", abort=True)

    async def rebuild() -> None:
        async with DatabaseManager(db_path).create_session() as session:
            foreign_keys = await session.fetch_value("PRAGMA foreign_keys")
            await session.execute("PRAGMA foreign_keys=OFF")
            try:
                async with session.transaction(immediate=True):
                    objects = await session.fetch_all(
                        "SELECT type, name FROM sqlite_master "
                        "WHERE type IN ('view', 'trigger', 'table') AND name NOT LIKE 'sqlite_%' "
                        "ORDER BY CASE type WHEN 'view' THEN 0 WHEN 'trigger' THEN 1 ELSE 2 END"
                    )
                    for object_type, name in objects:
                        escaped_name = name.replace('"', '""')
                        await session.execute(f'DROP {object_type.upper()} IF EXISTS "{escaped_name}"')
                    await registry._apply_in_transaction(session)
            finally:
                await session.execute(f"PRAGMA foreign_keys={'ON' if foreign_keys else 'OFF'}")

    try:
        _run_cli_async(rebuild)
    except DatabaseError:
        raise
    except Exception as error:
        raise DatabaseManagementError(f"Failed to rebuild database after reset: {error}") from error
    typer.echo(f"Database reset: {db_path}")


def add_database_subcommand(cli: typer.Typer, migration_registry: MigrationRegistry) -> None:
    database_cli = typer.Typer(
        help="Inspect and manage the application database",
        invoke_without_command=True,
        no_args_is_help=True,
    )
    database_cli.command()(path)
    database_cli.command()(inspect)
    database_cli.command(name="status")(lambda: status(migration_registry))
    database_cli.command()(setup)
    database_cli.command(name="migrate")(lambda: migrate(migration_registry))
    database_cli.command(name="reset")(lambda: reset(migration_registry))
    cli.add_typer(database_cli, name="db")
