import typer
from rich import print

from typerdrive import DatabaseManager, MigrationRegistry, attach_database, get_database_manager
from typerdrive.config import get_typerdrive_config


def demo_1__attach_database__async_sql():
    """
    This function demonstrates how to attach a database manager to an async Typer command and use parameterized SQL.
    The migration is shown as SQL text in this function and registered with the database registry. The attachment applies
    it before the command runs, then the command inserts and lists rows using bound SQL parameters.
    """

    migration_registry = MigrationRegistry()
    migration_sql = """
        CREATE TABLE starships (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
    """
    migration_registry.register_migration("create_starships", migration_sql)
    database_path = get_typerdrive_config().database_path
    assert not database_path.exists()

    cli = typer.Typer()

    @cli.command()
    @attach_database(migration_registry)
    async def add_item(ctx: typer.Context, database: DatabaseManager):
        assert database_path.exists()
        journal_mode = await database.fetch_value("PRAGMA journal_mode")
        migrated_table = await database.fetch_value(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'starships'"
        )
        assert journal_mode == "wal"
        assert migrated_table == "starships"
        print("Attachment created the file, enabled WAL, and applied the starships migration")
        await database.execute("INSERT INTO starships (name) VALUES (?)", ("Millennium Falcon",))
        rows = await database.fetch_all("SELECT name FROM starships ORDER BY id")
        print(f"[green]Starships:[/green] {', '.join([r['name'] for r  in rows])}")

    cli()


def demo_2__attach_database__sync_wrappers():
    """
    This function demonstrates the synchronous database convenience API in a Typer command. The attachment keeps the
    manager open for the duration of the command. The `execute_sync` and `fetch_all_sync` methods provide SQL access
    without the caller managing an event loop.
    """

    migration_registry = MigrationRegistry()
    migration_sql = """
        CREATE TABLE starships (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        INSERT INTO starships (name)
        VALUES ("Millennium Falcon"), ("TIE Fighter"), ("X-wing")
        ;
    """
    migration_registry.register_migration("create_starships", migration_sql)

    cli = typer.Typer()

    @cli.command()
    @attach_database(migration_registry)
    def add_sync_item(ctx: typer.Context, database: DatabaseManager):
        rows = database.fetch_all_sync("SELECT name FROM starships ORDER BY id")
        print(f"[green]Starships:[/green] {', '.join([r['name'] for r  in rows])}")

    cli()


def demo_3__attach_database__context_lookup():
    """
    This function demonstrates retrieving a database manager from the Typer context instead of declaring a parameter.
    The attachment opens the connection and applies pending migrations before the command runs; `get_database_manager(ctx)`
    returns that live manager.
    """

    migration_registry = MigrationRegistry()
    migration_sql = """
        CREATE TABLE starships (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        INSERT INTO starships (name)
        VALUES ("Millennium Falcon"), ("TIE Fighter"), ("X-wing")
        ;
    """
    migration_registry.register_migration("create_starships", migration_sql)

    cli = typer.Typer()

    @cli.command()
    @attach_database(migration_registry)
    async def list_items(ctx: typer.Context):
        database = get_database_manager(ctx)
        rows = await database.fetch_all("SELECT name FROM starships ORDER BY id")
        print(f"[green]Starships:[/green] {', '.join([r['name'] for r  in rows])}")

    cli()
