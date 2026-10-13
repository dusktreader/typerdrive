from pathlib import Path

import typer

from typerdrive import DatabaseManager, MigrationRegistry, attach_database


cli = typer.Typer()
registry = MigrationRegistry()
migration_text = (Path(__file__).parent / "migrations" / "0001_create_items.sql").read_text()
registry.register_migration("create_items", migration_text)


@cli.command()
@attach_database(registry)
async def add_item(ctx: typer.Context, database: DatabaseManager, name: str):
    await database.execute("INSERT INTO items (name) VALUES (?)", (name,))
    typer.echo("Item added")


@cli.command()
@attach_database(registry)
async def list_items(ctx: typer.Context, database: DatabaseManager):
    rows = await database.fetch_all("SELECT id, name FROM items ORDER BY id")
    for row in rows:
        typer.echo(f"{row['id']}: {row['name']}")


@cli.command()
@attach_database(registry)
def add_item_sync(ctx: typer.Context, database: DatabaseManager, name: str):
    database.execute_sync("INSERT INTO items (name) VALUES (?)", (name,))
    typer.echo("Item added")


@cli.command()
@attach_database(registry)
def list_items_sync(ctx: typer.Context, database: DatabaseManager):
    rows = database.fetch_all_sync("SELECT id, name FROM items ORDER BY id")
    for row in rows:
        typer.echo(f"{row['id']}: {row['name']}")


if __name__ == "__main__":
    cli()
