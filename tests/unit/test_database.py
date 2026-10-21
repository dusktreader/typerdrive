import asyncio
from pathlib import Path

import typer
from typer.testing import CliRunner

from typerdrive import (
    DatabaseManager,
    DatabaseSession,
    MigrationRegistry,
    attach_database,
    get_database_manager,
    get_database_session,
)


def test_manager_creates_independent_sessions(tmp_path: Path):
    manager = DatabaseManager(tmp_path / "database.sqlite")
    first = manager.create_session()
    second = manager.create_session()

    assert first is not second
    assert not hasattr(manager, "execute")
    assert not hasattr(manager, "__aenter__")
    assert not hasattr(manager, "transaction")
    assert first._operation_lock is not second._operation_lock
    assert first._sync_adapter is not second._sync_adapter

    async def check_sessions():
        async with first:
            assert first.is_open
            assert not second.is_open
            async with second:
                assert first.connection is not second.connection
            assert first.is_open
            assert not second.is_open
        assert not first.is_open

    asyncio.run(check_sessions())


def test_session_injection_binds_live_session_and_closes_it(tmp_path: Path, monkeypatch):
    path = tmp_path / "database.sqlite"
    monkeypatch.setattr("typerdrive.database.manager.get_typerdrive_config", lambda: _config_for(path))
    registry = MigrationRegistry()
    registry.register_migration("create_items", "CREATE TABLE items (name TEXT NOT NULL);")
    migration_sessions: list[DatabaseSession] = []
    apply_migrations = registry.apply

    async def track_migration_session(session: DatabaseSession):
        migration_sessions.append(session)
        await apply_migrations(session)

    monkeypatch.setattr(registry, "apply", track_migration_session)
    cli = typer.Typer()
    injected: list[DatabaseSession] = []
    contexts = []

    @cli.command()
    @attach_database(registry)
    async def inspect(ctx: typer.Context, session: DatabaseSession):
        contexts.append(ctx)
        injected.append(session)
        assert get_database_session(ctx) is session
        assert get_database_manager(ctx).database_path == _config_for(path).database_path
        assert migration_sessions[0] is not session
        assert not migration_sessions[0].is_open
        assert await session.fetch_value("SELECT name FROM sqlite_master WHERE name = 'items'") == "items"

    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0, result.output
    assert len(injected) == 1
    assert len(migration_sessions) == 1
    assert not injected[0].is_open
    assert contexts[0].obj.database_session is None
    assert contexts[0].obj.database_manager is None


def test_context_lookup_binds_live_session_without_typed_parameter(tmp_path: Path, monkeypatch):
    path = tmp_path / "database.sqlite"
    monkeypatch.setattr("typerdrive.database.manager.get_typerdrive_config", lambda: _config_for(path))
    registry = MigrationRegistry()
    registry.register_migration("create_items", "CREATE TABLE items (name TEXT NOT NULL);")
    cli = typer.Typer()
    sessions: list[DatabaseSession] = []
    contexts = []

    @cli.command()
    @attach_database(registry)
    async def inspect(ctx: typer.Context):
        session = get_database_session(ctx)
        sessions.append(session)
        contexts.append(ctx)
        assert session.is_open
        assert await session.fetch_value("SELECT name FROM sqlite_master WHERE name = 'items'") == "items"

    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0, result.output
    assert sessions and not sessions[0].is_open
    assert contexts[0].obj.database_session is None


def test_sync_session_injection_binds_live_session_and_closes_it(tmp_path: Path, monkeypatch):
    path = tmp_path / "database.sqlite"
    monkeypatch.setattr("typerdrive.database.manager.get_typerdrive_config", lambda: _config_for(path))
    registry = MigrationRegistry()
    registry.register_migration("create_values", "CREATE TABLE values_table (value INTEGER);")
    migration_sessions: list[DatabaseSession] = []
    apply_migrations = registry.apply

    async def track_migration_session(session: DatabaseSession):
        migration_sessions.append(session)
        await apply_migrations(session)

    monkeypatch.setattr(registry, "apply", track_migration_session)
    cli = typer.Typer()
    injected: list[DatabaseSession] = []
    values = []

    @cli.command()
    @attach_database(registry)
    def inspect(ctx: typer.Context, session: DatabaseSession):
        injected.append(session)
        assert get_database_session(ctx) is session
        assert migration_sessions[0] is not session
        assert not migration_sessions[0].is_open
        session.execute_sync("INSERT INTO values_table VALUES (42)")
        values.append(session.fetch_value_sync("SELECT value FROM values_table"))

    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0, result.output
    assert values == [42]
    assert len(migration_sessions) == 1
    assert injected and not injected[0].is_open


def test_command_transaction_rollback_does_not_rollback_migrations(tmp_path: Path, monkeypatch):
    path = tmp_path / "database.sqlite"
    monkeypatch.setattr("typerdrive.database.manager.get_typerdrive_config", lambda: _config_for(path))
    registry = MigrationRegistry()
    registry.register_migration("create_items", "CREATE TABLE items (value INTEGER); INSERT INTO items VALUES (1);")
    cli = typer.Typer()

    @cli.command()
    @attach_database(registry)
    async def fail(ctx: typer.Context, session: DatabaseSession):
        async with session.transaction():
            await session.execute("INSERT INTO items VALUES (2)")
            raise ValueError("command failed")

    result = CliRunner().invoke(cli, [])

    assert result.exit_code != 0

    async def verify_database():
        async with DatabaseManager(_config_for(path).database_path).create_session() as session:
            rows = await session.fetch_all("SELECT value FROM items ORDER BY value")
            assert [row[0] for row in rows] == [1]

    asyncio.run(verify_database())


def test_manager_injection_migrates_with_temporary_session(tmp_path: Path, monkeypatch):
    path = tmp_path / "database.sqlite"
    monkeypatch.setattr("typerdrive.database.manager.get_typerdrive_config", lambda: _config_for(path))
    registry = MigrationRegistry()
    registry.register_migration("create_items", "CREATE TABLE items (name TEXT NOT NULL);")
    cli = typer.Typer()
    injected: list[DatabaseManager] = []

    @cli.command()
    @attach_database(registry)
    async def inspect(ctx: typer.Context, manager: DatabaseManager):
        injected.append(manager)
        assert get_database_manager(ctx) is manager
        assert not hasattr(manager, "execute")
        async with manager.create_session() as session:
            assert await session.fetch_value("SELECT name FROM sqlite_master WHERE name = 'items'") == "items"

    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0, result.output
    assert len(injected) == 1
    assert injected[0].database_path == _config_for(path).database_path


def _config_for(path: Path):
    from typerdrive.config import TyperdriveConfig

    return TyperdriveConfig(app_name="test", state_home=path.parent)
