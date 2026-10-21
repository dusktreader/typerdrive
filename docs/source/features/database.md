# SQLite databases for applications

Big CLI applications often need to preserve structured data between commands, such as local records, task history, or
application-specific state. To help with that, `typerdrive` uses SQLite to provide durable storage without requiring a
separate database service and manages the sessions so command code can focus on the data it needs.


## Overview

You can take advantage of the builtin SQLite database provided by `typerdrive` without any additional dependencies or an
ORM. Your application defines the schema and writes the SQL; Typerdrive takes care of managing database connections.

`DatabaseManager` is the session factory. It creates independent `DatabaseSession` instances, each with its own
connection and transaction state. A command can receive one session for straightforward query work, or
receive the manager and create separate sessions when coordinating multiple services.

Sessions work with both async and synchronous commands. The sync wrappers use the same aiosqlite connection as the async
methods, so choose one API for each session lifecycle. Sync wrappers cannot run inside an active event loop.


## Usage

The runnable example shows async and sync commands with an attached `DatabaseSession`, plus a command that
receives a `DatabaseManager` and creates separate sessions for helper operations:

```python {linenums="1"}
--8<-- "examples/database/attach.py"
```

Run the example from the repository root:

```shell
examples/database/attach.py add-item astromech
examples/database/attach.py report-items
```

The commands print formatted panels:

```text
╭─ Database ───────────────────────────────────────────────────────────────────╮
│                                                                              │
│   Added astromech                                                            │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

╭─ Item report ────────────────────────────────────────────────────────────────╮
│                                                                              │
│   Count: 1                                                                   │
│   Names: astromech                                                           │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

`add-item` and the list commands use an attached session for direct queries. `report-items`
uses the manager to create a session for each helper operation.


## Details

### Database location and journal mode

The database location is managed by Typerdrive's internal [`TyperdriveConfig`](../config.md), which derives the default
path from the app identity and state directory. The database path is separate from cache and files storage.

WAL is the default journal mode. `DatabaseManager` and `attach_database` accept another supported SQLite journal mode
when the storage environment requires it.


### Session APIs and transactions

`execute`, `fetch_one`, `fetch_all`, and `fetch_value` accept parameterized SQL. Query methods return SQLite rows, which
support integer and column-name indexing. SQLite and connection failures become database feature errors.

The sync methods are `execute_sync`, `fetch_one_sync`, `fetch_all_sync`, `fetch_value_sync`, and `transaction_sync`.
Calling them inside an active event loop raises `DatabaseLifecycleError` and points to the async API. Do not mix the
sync and async APIs during one session lifecycle.

A transaction serializes operations from other tasks on the same session. Other tasks wait until the transaction commits
or rolls back, and their operations do not join the transaction. Normal exit commits. An exception or cancellation rolls
back:

```python
async with session.transaction():
    await session.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, source_id))
    await session.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, target_id))
```

SQLite coordinates independent sessions and processes. Unresolvable locking and contention failures are reported as
feature errors.


### Command attachment

`@attach_database` looks for a parameter annotated as exactly `DatabaseSession` or `DatabaseManager`.

For direct query work, declare a `DatabaseSession` parameter. The decorator passes the live session to the command and
closes it afterward, including on failure or cancellation:

```python
@cli.command()
@attach_database(registry)
async def list_items(ctx: typer.Context, session: DatabaseSession):
    items = await session.fetch_all("SELECT id, name FROM items ORDER BY id")
    typer.echo(f"Found {len(items)} items")
```

For work that needs more than one session, declare a `DatabaseManager` parameter. The manager provides configuration
and a session factory, but has no lifecycle, query, or transaction methods:

```python
@cli.command()
@attach_database(registry)
async def report_items(ctx: typer.Context, manager: DatabaseManager):
    async with manager.create_session() as count_session:
        count = await count_session.fetch_value("SELECT COUNT(*) FROM items")

    async with manager.create_session() as names_session:
        names = await names_session.fetch_all("SELECT name FROM items ORDER BY id")

    typer.echo(f"Found {count} items: {', '.join(row['name'] for row in names)}")
```

`get_database_manager(ctx)` retrieves the manager in either case. `get_database_session(ctx)` retrieves the live session
when the command declares a `DatabaseSession` parameter or uses context lookup without a `DatabaseManager` parameter.

The synchronous Typer boundary cannot run inside an existing event loop; invoke CLI commands synchronously and use
explicit async sessions for async applications.


### Bootstrapping the database

Before invoking the decorated command, `@attach_database` checks to see if a database has been created for the app yet.
If it has not, it creates the database automatically.

Your `typerdrive` app can provide migrations to set up its schema. Before invoking the decorated command,
`@attach_database` applies pending migrations in a dedicated session, separate from the command's session. This applies
to new databases and to existing databases with newly registered migrations. If a migration fails, attachment aborts
before the decorated command runs.

The migrations are provided to a `MigrationRegistry` as text using the `register_migration()` method. You get to choose
how you want to load and store those migrations. The migrations are applied to the database in the order that you
register them.

Registration order assigns each migration an index. Its ID combines that index with a name derived from the description,
and the registry stores a SHA-256 checksum of the exact SQL text.

Pass a description and SQL text to the registry:

```python
from importlib.resources import files

from typerdrive import MigrationRegistry

registry = MigrationRegistry()
registry.register_migration(
    "create notes",
    files("my_app.migrations").joinpath("create_notes.sql").read_text(),
)
```

Once a migration has been applied, keep it registered with the same description and SQL. The registry validates applied
migration IDs and checksums, so removing or changing an applied migration fails integrity validation. To evolve the
schema, append a new migration. `db reset` rebuilds the schema from the registered migrations but deletes all application
data, so use it only when that data can be discarded.

Migrations are forward-only. Each migration and its tracking record are applied atomically; a failed migration rolls
back its changes and leaves earlier successful migrations available for retry.

The registry accepts strings only. It does not load files, call Python migration functions, or define application
schemas. The tracking table is owned by `typerdrive`; all other tables and SQL remain application-owned.


### Database management commands

Register the optional management group with the same registry used by `attach_database`:

```python
from typerdrive import add_database_subcommand

add_database_subcommand(cli, registry)
```

The commands are:

- `db path` prints the configured path without creating it.
- `db inspect` reports database existence, SQLite version, schema version, and journal mode without application rows.
- `db status` lists applied and pending migrations without modifying the database.
- `db setup` creates and configures an empty database only; it does not apply application migrations and is a no-op when
  the database already exists.
- `db migrate` requires an existing database and applies pending registered migrations. It does not create an absent
  database.
- `db reset` requires confirmation and transactionally rebuilds the schema and migration history in the existing
  database file using the currently registered migrations.

If the database file is absent, `inspect` reports that fact and `status` lists every registered migration as pending;
neither command creates the file. Concurrent setup initializes through SQLite and does not apply migrations. A reset
that is declined preserves data and history. Existing readers retain a consistent SQLite snapshot while reset runs;
concurrent writers serialize through SQLite's busy timeout. Reset does not unlink the database or its WAL sidecars.

Reset replaces all application data. Back up any data that must survive before confirming it.


### ORM layering

The database feature exposes direct SQL and SQLite rows. It does not provide an ORM, model layer, or application schema.
An application may build its own repository layer or integrate an ORM while using a session's connection.
