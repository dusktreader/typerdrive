import asyncio

import typer
from typer.testing import CliRunner

from typerdrive import DatabaseManager, MigrationRegistry, add_database_subcommand


def demo_1__database_commands__path_and_status():
    """
    This function demonstrates how to inspect the database location and migration status. `db path` reports the configured
    location without creating the database. `db status` reports applied and pending migrations without modifying the
    database; if no database exists, it remains absent and every registered migration is pending.
    """

    migration_registry = MigrationRegistry()
    migration_sql = """
        CREATE TABLE starships (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
    """
    migration_registry.register_migration("create_demo_items", migration_sql)
    cli = typer.Typer()
    add_database_subcommand(cli, migration_registry)
    cli(["db", "path"], standalone_mode=False)
    cli(["db", "status"], standalone_mode=False)


def demo_2__database_commands__inspect():
    """
    This function demonstrates how `db inspect` reports SQLite metadata without displaying application rows. It first
    uses `db setup` to create the database and `db migrate` to apply the inline SQL, then inspects the initialized
    database's operational details, such as the SQLite version and journal mode.
    """

    migration_registry = MigrationRegistry()
    migration_sql = """
        CREATE TABLE starships (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
    """
    migration_registry.register_migration("create_demo_items", migration_sql)
    cli = typer.Typer()
    add_database_subcommand(cli, migration_registry)
    cli(["db", "setup"], standalone_mode=False)
    cli(["db", "migrate"], standalone_mode=False)
    cli(["db", "inspect"], standalone_mode=False)


def demo_3__database_commands__setup_migrate_reset():
    """
    Demonstrate that setup creates an empty database, migrate applies the inline SQL, inspect reports metadata, and a
    confirmed reset rebuilds the schema from the current migration registry.
    """

    migration_registry = MigrationRegistry()
    migration_sql = """
        CREATE TABLE starships (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        INSERT INTO starships (name) VALUES ('Millennium Falcon');
    """
    migration_registry.register_migration("create_starships", migration_sql)
    cli = typer.Typer()
    add_database_subcommand(cli, migration_registry)
    runner = CliRunner()

    setup = runner.invoke(cli, ["db", "setup"], prog_name="demo")
    pending = runner.invoke(cli, ["db", "status"], prog_name="demo")
    setup_inspect = runner.invoke(cli, ["db", "inspect"], prog_name="demo")
    migrate = runner.invoke(cli, ["db", "migrate"], prog_name="demo")
    applied = runner.invoke(cli, ["db", "status"], prog_name="demo")
    migrated_inspect = runner.invoke(cli, ["db", "inspect"], prog_name="demo")
    reset = runner.invoke(cli, ["db", "reset"], input="y\n", prog_name="demo")

    for result in (setup, pending, setup_inspect, migrate, applied, migrated_inspect, reset):
        assert result.exit_code == 0, result.output
    assert "pending 00000001create_starships" in pending.output
    assert "applied 00000001create_starships" in applied.output
    assert "Journal mode: wal" in setup_inspect.output
    assert "SQLite version:" in migrated_inspect.output

    async def verify_rebuilt_schema() -> None:
        async with DatabaseManager() as database:
            table = await database.fetch_value(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'starships'"
            )
            row = await database.fetch_value("SELECT name FROM starships")
            assert table == "starships"
            assert row == "Millennium Falcon"

    asyncio.run(verify_rebuilt_schema())
    for result in (setup, pending, setup_inspect, migrate, applied, migrated_inspect, reset):
        typer.echo(result.output.strip())
