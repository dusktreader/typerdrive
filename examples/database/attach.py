from pathlib import Path

import typer

from typerdrive import DatabaseManager, DatabaseSession, MigrationRegistry, attach_database, terminal_message


cli = typer.Typer()
registry = MigrationRegistry()
migration_text = (Path(__file__).parent / "migrations" / "0001_create_items.sql").read_text()
registry.register_migration("create_items", migration_text)


@cli.command()
@attach_database(registry)
async def add_item(ctx: typer.Context, database: DatabaseSession, name: str):
    await database.execute("INSERT INTO items (name) VALUES (?)", (name,))
    terminal_message(f"Added {name}", subject="Database")


@cli.command()
@attach_database(registry)
async def list_items(ctx: typer.Context, database: DatabaseSession):
    rows = await database.fetch_all("SELECT id, name FROM items ORDER BY id")
    items = "\n".join(f"{row['id']}: {row['name']}" for row in rows) or "No items found"
    terminal_message(items, subject="Items")


@cli.command()
@attach_database(registry)
def add_item_sync(ctx: typer.Context, database: DatabaseSession, name: str):
    database.execute_sync("INSERT INTO items (name) VALUES (?)", (name,))
    terminal_message(f"Added {name}", subject="Database")


@cli.command()
@attach_database(registry)
def list_items_sync(ctx: typer.Context, database: DatabaseSession):
    rows = database.fetch_all_sync("SELECT id, name FROM items ORDER BY id")
    items = "\n".join(f"{row['id']}: {row['name']}" for row in rows) or "No items found"
    terminal_message(items, subject="Items")


async def load_item_names(session: DatabaseSession) -> list[str]:
    rows = await session.fetch_all("SELECT name FROM items ORDER BY id")
    return [row["name"] for row in rows]


async def count_items(session: DatabaseSession) -> int:
    return await session.fetch_value("SELECT COUNT(*) FROM items")


@cli.command()
@attach_database(registry)
async def report_items(ctx: typer.Context, manager: DatabaseManager):
    async with manager.create_session() as names_session:
        names = await load_item_names(names_session)

    async with manager.create_session() as count_session:
        count = await count_items(count_session)

    terminal_message(f"Count: {count}\nNames: {', '.join(names)}", subject="Item report")


if __name__ == "__main__":
    cli()
