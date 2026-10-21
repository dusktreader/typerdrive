import asyncio
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, closing
from pathlib import Path

import typer
from typer.testing import CliRunner
from typerdrive.database.commands import add_database_subcommand
from typerdrive.database.migrations import MigrationRegistry
from typerdrive.database.session import DatabaseSession


class TestDatabaseCommands:
    def test_path_does_not_create_parent_or_database(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "missing" / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        cli = typer.Typer()
        add_database_subcommand(cli, MigrationRegistry())

        result = CliRunner().invoke(cli, ["db", "path"])

        assert result.exit_code == 0
        assert str(path) in result.output
        assert not path.exists()
        assert not path.parent.exists()

    def test_absent_inspect_and_status_are_read_only(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "missing.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (id INTEGER);")
        cli = typer.Typer()
        add_database_subcommand(cli, registry)
        runner = CliRunner()

        inspect_result = runner.invoke(cli, ["db", "inspect"])
        status_result = runner.invoke(cli, ["db", "status"])

        assert inspect_result.exit_code == 0
        assert "does not exist" in inspect_result.output
        assert status_result.exit_code == 0
        assert "pending" in status_result.output
        assert "00000001create item" in status_result.output
        assert not path.exists()

    def test_inspect_reports_metadata_without_application_rows(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        with closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute("CREATE TABLE item (secret TEXT)")
                connection.execute("INSERT INTO item VALUES ('private row')")
        cli = typer.Typer()
        add_database_subcommand(cli, MigrationRegistry())

        result = CliRunner().invoke(cli, ["db", "inspect"])

        assert result.exit_code == 0
        assert "SQLite version" in result.output
        assert "Journal mode" in result.output
        assert "private row" not in result.output

    def test_status_shows_applied_and_pending_migrations(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (id INTEGER);")
        registry.register_migration("Add Name", "ALTER TABLE item ADD COLUMN name TEXT;")

        async def apply_first():
            async with DatabaseSession(path) as manager:
                await MigrationRegistryWithFirst(registry).apply(manager)

        asyncio.run(apply_first())
        cli = typer.Typer()
        add_database_subcommand(cli, registry)
        result = CliRunner().invoke(cli, ["db", "status"])

        assert result.exit_code == 0
        assert "applied" in result.output
        assert "pending" in result.output
        assert "00000001create item" in result.output
        assert "00000002add name" in result.output

    def test_reset_requires_confirmation_and_rebuilds_current_schema(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        original = MigrationRegistry()
        original.register_migration("Create Old", "CREATE TABLE old_item (value TEXT);")

        async def seed():
            async with DatabaseSession(path) as manager:
                await original.apply(manager)
                await manager.execute("INSERT INTO old_item VALUES ('old data')")

        asyncio.run(seed())
        current = MigrationRegistry()
        current.register_migration("Create New", "CREATE TABLE new_item (value TEXT);")
        cli = typer.Typer()
        add_database_subcommand(cli, current)
        result = CliRunner().invoke(cli, ["db", "reset"], input="y\n")

        assert result.exit_code == 0, result.output

        async def verify():
            async with DatabaseSession(path) as manager:
                assert await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'old_item'") is None
                assert await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'new_item'") == "new_item"
                assert await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations") == 1

        asyncio.run(verify())

    def test_declined_reset_preserves_rows_and_history(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (value TEXT);")

        async def seed():
            async with DatabaseSession(path) as manager:
                await registry.apply(manager)
                await manager.execute("INSERT INTO item VALUES ('keep')")

        asyncio.run(seed())
        cli = typer.Typer()
        add_database_subcommand(cli, registry)
        result = CliRunner().invoke(cli, ["db", "reset"], input="n\n")

        assert result.exit_code != 0

        async def verify():
            async with DatabaseSession(path) as manager:
                assert await manager.fetch_value("SELECT value FROM item") == "keep"
                assert await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations") == 1

        asyncio.run(verify())

    def test_reset_rolls_back_schema_data_and_history_when_migration_fails(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        original = MigrationRegistry()
        original.register_migration("Create Item", "CREATE TABLE item (value TEXT);")

        async def seed():
            async with DatabaseSession(path) as manager:
                await original.apply(manager)
                await manager.execute("INSERT INTO item VALUES ('keep')")

        asyncio.run(seed())
        broken = MigrationRegistry()
        broken.register_migration("Create Replacement", "CREATE TABLE replacement (value TEXT); INVALID SQL;")
        cli = typer.Typer()
        add_database_subcommand(cli, broken)

        result = CliRunner().invoke(cli, ["db", "reset"], input="y\n")

        assert result.exit_code == 1
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("SELECT value FROM item").fetchone() == ("keep",)
            assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'replacement'").fetchone() is None
            assert connection.execute("SELECT migration_id FROM _typerdrive_migrations").fetchone() == (
                "00000001create item",
            )

    def test_reset_preserves_reader_snapshot_and_database_file(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        original = MigrationRegistry()
        original.register_migration("Create Item", "CREATE TABLE item (value TEXT);")

        async def seed():
            async with DatabaseSession(path) as manager:
                await original.apply(manager)
                await manager.execute("INSERT INTO item VALUES ('old snapshot')")

        asyncio.run(seed())
        file_identity = path.stat().st_ino
        reader = sqlite3.connect(path)
        reader.execute("BEGIN")
        assert reader.execute("SELECT value FROM item").fetchone() == ("old snapshot",)
        current = MigrationRegistry()
        current.register_migration("Create Replacement", "CREATE TABLE replacement (value TEXT);")
        cli = typer.Typer()
        add_database_subcommand(cli, current)

        result = CliRunner().invoke(cli, ["db", "reset"], input="y\n")

        assert result.exit_code == 0, result.output
        assert path.stat().st_ino == file_identity
        assert reader.execute("SELECT value FROM item").fetchone() == ("old snapshot",)
        assert reader.execute("SELECT name FROM sqlite_master WHERE name = 'replacement'").fetchone() is None
        reader.close()
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'item'").fetchone() is None
            assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'replacement'").fetchone() == (
                "replacement",
            )

    def test_reset_waits_for_active_writer_transaction(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        reset_started = threading.Event()

        def database_path():
            reset_started.set()
            return path

        monkeypatch.setattr("typerdrive.database.commands.database_path", database_path)
        original = MigrationRegistry()
        original.register_migration("Create Item", "CREATE TABLE item (value TEXT);")

        async def seed():
            async with DatabaseSession(path) as manager:
                await original.apply(manager)
                await manager.execute("INSERT INTO item VALUES ('before writer')")

        asyncio.run(seed())
        writer = sqlite3.connect(path, timeout=5)
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO item VALUES ('active writer')")
        transaction_requested = threading.Event()
        original_transaction = DatabaseSession.transaction

        @asynccontextmanager
        async def tracked_transaction(manager: DatabaseSession, immediate: bool = False):
            transaction_requested.set()
            async with original_transaction(manager, immediate=immediate):
                yield manager

        monkeypatch.setattr(DatabaseSession, "transaction", tracked_transaction)
        current = MigrationRegistry()
        current.register_migration("Create Replacement", "CREATE TABLE replacement (value TEXT);")

        def reset_database():
            cli = typer.Typer()
            add_database_subcommand(cli, current)
            return CliRunner().invoke(cli, ["db", "reset"], input="y\n")

        reset_finished = threading.Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            reset = executor.submit(reset_database)
            reset.add_done_callback(lambda _: reset_finished.set())
            assert reset_started.wait(5)
            assert transaction_requested.wait(5)
            assert not reset_finished.wait(0.1)
            writer.commit()
            result = reset.result(timeout=10)
        writer.close()

        assert result.exit_code == 0, result.output
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'item'").fetchone() is None
            assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'replacement'").fetchone() == (
                "replacement",
            )

    def test_setup_creates_empty_database_without_application_schema(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (id INTEGER);")
        cli = typer.Typer()
        add_database_subcommand(cli, registry)

        result = CliRunner().invoke(cli, ["db", "setup"])

        assert result.exit_code == 0, result.output
        assert path.exists()
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
        assert tables == []

    def test_setup_existing_database_preserves_schema_and_data(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        with closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("CREATE TABLE item (value TEXT)")
                connection.execute("INSERT INTO item VALUES ('keep')")
        cli = typer.Typer()
        add_database_subcommand(cli, MigrationRegistry())

        result = CliRunner().invoke(cli, ["db", "setup"])

        assert result.exit_code == 0, result.output
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("SELECT value FROM item").fetchone() == ("keep",)
            assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "delete"

    def test_concurrent_setup_initializes_one_database_without_application_schema(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (id INTEGER);")
        start = threading.Barrier(2)

        def setup_database():
            cli = typer.Typer()
            add_database_subcommand(cli, registry)
            start.wait(timeout=5)
            return CliRunner().invoke(cli, ["db", "setup"])

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: setup_database(), range(2)))

        assert all(result.exit_code == 0 for result in results), [result.output for result in results]
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        assert tables == []
        assert not Path(f"{path}.lock").exists()

    def test_migrate_rejects_absent_database_without_creating_it(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (id INTEGER);")
        cli = typer.Typer()
        add_database_subcommand(cli, registry)

        result = CliRunner().invoke(cli, ["db", "migrate"])

        assert result.exit_code == 1
        assert "db setup" in result.output or "attached command" in result.output
        assert not path.exists()

    def test_migrate_after_setup_applies_registered_schema_and_ledger(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (id INTEGER);")
        cli = typer.Typer()
        add_database_subcommand(cli, registry)
        runner = CliRunner()

        setup_result = runner.invoke(cli, ["db", "setup"])
        migrate_result = runner.invoke(cli, ["db", "migrate"])

        assert setup_result.exit_code == 0, setup_result.output
        assert migrate_result.exit_code == 0, migrate_result.output
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'item'"
            ).fetchone() == ("item",)
            assert connection.execute("SELECT migration_id FROM _typerdrive_migrations").fetchone() == (
                "00000001create item",
            )

    def test_status_reports_migrations_pending_after_setup_and_applied_after_migrate(self, tmp_path: Path, monkeypatch):
        path = tmp_path / "db.sqlite"
        monkeypatch.setattr("typerdrive.database.commands.database_path", lambda: path)
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (id INTEGER);")
        cli = typer.Typer()
        add_database_subcommand(cli, registry)
        runner = CliRunner()

        setup_result = runner.invoke(cli, ["db", "setup"])
        pending_result = runner.invoke(cli, ["db", "status"])
        migrate_result = runner.invoke(cli, ["db", "migrate"])
        applied_result = runner.invoke(cli, ["db", "status"])

        assert setup_result.exit_code == 0, setup_result.output
        assert pending_result.exit_code == 0, pending_result.output
        assert "pending 00000001create item" in pending_result.output
        assert migrate_result.exit_code == 0, migrate_result.output
        assert applied_result.exit_code == 0, applied_result.output
        assert "applied 00000001create item" in applied_result.output
        assert "pending" not in applied_result.output

    def test_group_help_and_no_argument_help(self):
        cli = typer.Typer()
        add_database_subcommand(cli, MigrationRegistry())
        runner = CliRunner()

        help_result = runner.invoke(cli, ["db", "--help"])
        assert help_result.exit_code == 0
        assert "setup" in help_result.output
        assert "migrate" in help_result.output
        result = runner.invoke(cli, ["db"])
        assert result.exit_code == 2
        assert "Usage" in result.output


class MigrationRegistryWithFirst(MigrationRegistry):
    def __init__(self, source: MigrationRegistry):
        super().__init__()
        self.register_migration(source.migrations[0].description, source.migrations[0].sql_text)
