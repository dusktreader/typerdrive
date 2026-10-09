# Design Plan: SQLite database feature

Add a lifecycle-managed SQLite database to typerdrive for applications that need durable structured data. The feature
uses aiosqlite as its async-first database interface, supports synchronous callers without unsafe event-loop nesting,
and includes application-owned schema migrations and optional database management commands.


## Goal

Give typerdrive applications a consistent way to open and close a SQLite database at the application’s XDG state
location, use SQL directly without an ORM, and make the active database manager available to command functions and
Typer context. The feature must support both ordinary synchronous CLI commands and async work, including long-lived
async applications, without concealing event-loop conflicts.

Include schema migrations in v1, along with an optional `db` command group for inspecting and managing the database.
Keep schema design, SQL queries, and any ORM integration in the application. Document and demonstrate the feature using
typerdrive’s existing conventions for attachments, manager access, subcommands, examples, and release notes.


## Acceptance Criteria

### Storage and lifecycle

#### AC01: Database uses the application state location

The default database is created at `~/.local/state/<app_name>/db.sqlite`, honoring the configured XDG state home and
application name. It is isolated from other applications and does not share the cache or files feature’s storage.


#### AC02: Attachment manages the database lifecycle

A command using the database attachment receives its manager through the established context and typed-injection
patterns. The database is available for the entire command and is closed after success, failure, or cancellation.
Applications can also manage the database through an explicit async lifecycle for work that outlives a single CLI
command.


### Async and synchronous use

#### AC03: Async commands work through Typer

A decorated async command is awaited to completion when invoked through Typer, and the database remains open until the
command finishes. Synchronous decorated commands remain usable. Invoking the synchronous Typer boundary from an
already-running event loop produces a clear, actionable error rather than an unawaited coroutine or nested-loop error.


#### AC04: Async database use is primary

The manager provides async SQL operations and transaction scopes without imposing an ORM or schema model. Multiple
async tasks can share one manager. Transaction scopes are serialized per manager: operations from other tasks wait until
the active transaction commits or rolls back, and cannot become part of that transaction. Transactions commit on normal
exit and roll back on error or cancellation. Concurrent access that cannot proceed is reported through a clear
feature-specific error rather than corrupting results.


#### AC05: Synchronous wrappers do not nest event loops

Synchronous wrapper methods work for non-async callers when no event loop is running and preserve one connection
lifecycle for the command. Calling those wrappers while an event loop is already running fails clearly and directs the
caller to the async API; it never invokes a nested event loop or silently blocks the caller’s loop.

A manager lifecycle uses either async access or synchronous wrapper access. Switching between those APIs while the
manager is open fails with a lifecycle error that names the supported API. Synchronous wrapper calls made from within an
active event loop fail clearly and direct callers to the async API.


### Schema migrations

#### AC06: Registered migrations bring the database to the current schema

A client application obtains each migration's pure SQL text using its chosen method and registers it with a description.
The registry assigns indices starting at 1 and increments by one in registration order. It generates each stable
migration identifier as `f"{idx:08d}{inflection.underscore(desc)}"`. Applications register the full history in order and
append new migrations; empty descriptions or SQL text produce a feature-specific error before any migration is applied,
and the attached application command does not proceed. The same registered migrations are used by command attachments
and database-management commands. Attaching to an absent
database creates and configures it, then applies the full registered sequence before the command runs. Attaching to an
existing database applies pending migrations before the command runs. This differs from `db setup`, which creates an
empty database without application migrations, and `db migrate`, which applies pending migrations only to an existing
database. A new database reaches the same current schema as an existing database after all registered migrations run.


#### AC07: Migrations are tracked and concurrency-safe

The database records applied migration indices, generated identifiers, and SQL checksums. The registered history must
contain every applied index with the same identifier and checksum; removed migrations, changed descriptions, or changed
SQL fail with a migration-integrity error before any further migration is applied, and the attached application command
does not proceed. Concurrent application starts cannot apply the same migration more than once.


#### AC08: A failed migration does not claim success

Each migration and its tracking record commit atomically. If a migration fails, its changes and record roll back, later
migrations do not run, and the application command does not proceed. Earlier successful migrations remain recorded so
a corrected pending migration can be retried.


### Management and project integration

#### AC09: Database commands expose safe inspection and control

The optional `db` command group reports the database path, inspects safe metadata, reports migration status, creates the
database with `setup`, applies pending application migrations with `migrate`, and supports confirmed `reset`. `inspect`
and `status` are read-only; for an absent file they report non-existence and all registered migrations pending without
creating it. `setup` obtains exclusive lifecycle access, creates the configured SQLite file if absent, and does not
apply
application migrations; if it already exists, setup is a no-op that preserves its data and schema. If active managers or
migrations prevent exclusivity, setup fails without changes. `migrate` requires an existing database, applies pending
registered migrations, and fails without creating a file when the database is absent. `reset` requires confirmation and
exclusive database access before deleting stored data and migration history, then recreates the database using the
currently registered migration sequence. If an active manager or migration prevents exclusive access, reset fails
without
modifying the database or its sidecars.


#### AC10: Errors follow typerdrive conventions

Connection, query, migration, lifecycle, and management-command failures use feature-specific errors that integrate
with typerdrive’s existing user-facing error handling and exit-code conventions.


#### AC11: Users can learn and run the feature

The feature includes new API and command reference documentation, usage examples, runnable demos, and a changelog entry.
Examples demonstrate async and synchronous access and client-supplied SQL migration registration. A runnable attachment
demo starts with an absent database and verifies from inside the command that the database file exists, WAL is
configured,
and a table from the registered migrations is available before normal command logic runs. A management demo shows `db
setup` leaving application migrations pending, `db migrate` applying them, and confirmed `db reset` rebuilding from the
current registry. Demo functions show migration SQL inline. Documentation
explains async and sync usage, how attachment differs from `db setup` and `db migrate`, migration registration and
failure
semantics, database location, reset behavior, and ORM layering.


#### AC12: WAL is the default journal mode

A newly initialized database uses WAL by default. An application can choose another supported journal mode when its
storage environment requires it.


## Architecture

### Database ownership and use

The database feature follows the existing attachment pattern: one manager owns the SQLite connection for a command,
places itself in typerdrive context, and makes it available through typed injection or context lookup. Its default file
lives under the application’s XDG state directory. The manager exposes aiosqlite-level operations so applications own
their tables, queries, and data models; an application may wrap the connection with its preferred ORM.

Attaching to a missing database creates and configures the file, then applies all registered migrations before
application
code runs. Attaching to an existing database applies pending migrations. `db setup` creates an empty database without
application schema, while `db migrate` applies pending migrations only when a database already exists.

Async commands use an async manager lifecycle. The attachment integrates async command execution with Typer’s
synchronous callback boundary and reports a clear limitation if invoked from an already-running event loop. Synchronous
callers can use the wrapper API when no event loop is active. Each manager lifecycle uses either async access or
synchronous wrapper access, as specified in AC05.

Transaction scopes are serialized per manager. While one transaction is active, operations requested by other tasks wait
until it commits or rolls back; those operations cannot execute on the shared connection as part of another task's
transaction. SQLite contention that cannot be resolved through this coordination is surfaced as a useful
feature-specific error rather than mistaken for successful concurrent writes.


### Migration model

V1 migrations are pure SQL strings. Each client application chooses how to obtain that text and registers migrations
with a description and SQL string. The registry assigns indices beginning at 1 in registration order and generates each
stable identifier as `f"{idx:08d}{inflection.underscore(desc)}"`. Applications register the full migration sequence in
order with the same registry used by command attachments and database-management commands; typerdrive does not load
migration files or run Python migration callbacks.

The database persistently records each applied index, generated identifier, and SQL checksum. On startup, the complete
registered history must match every already-applied index and identity; a removed migration, changed description, or
changed SQL fails with a migration-integrity error before further changes or application code. Concurrent application
starts do not apply the same migration more than once. Each migration and its recorded success are atomic: a failure
leaves earlier successful migrations intact and the failed migration eligible for retry.

Migrations are forward-only in v1; there is no command to downgrade previously applied migrations. Transaction rollback
only protects the database when an individual migration fails: that migration's partial changes are undone, while
earlier successful migrations remain applied. Applications can correct mistakes with a new forward migration or
`db reset`. Reset deletes the database and its migration history, then applies the currently registered migration
sequence. Normal attachment applies pending migrations before application code runs; `status` remains non-mutating and
provides visibility into pending changes without starting the application command.


### Typer integration and operations

The optional `db` group follows the existing feature subcommand convention. `path` resolves and prints the configured
location without creating the database. `inspect` reports safe operational metadata, such as whether the database
exists, its SQLite and schema versions, and its journal mode, but not application records. `status` reports applied and
pending migrations without applying them. For an absent database, `inspect` reports non-existence and `status` lists all
registered migrations as pending, without creating the file. `setup` obtains exclusive lifecycle access and creates an
empty database if absent, without application migrations; for an existing database it is a no-op. If active users
prevent
exclusive access, setup fails without changes. `migrate` requires an existing database and applies pending registered
migrations; if no database exists, it fails without creating the file. `reset` obtains exclusive database access before
deleting the database, migration history, and sidecars; it then applies the currently registered migration sequence. If
existing users prevent exclusive access, reset fails without changes. While setup or reset holds exclusive access, new
attachments and migration runs cannot begin.

The manager surfaces SQLite contention as a useful feature error rather than presenting concurrent access as unlimited
write parallelism. WAL is the default journal mode to support concurrent readers and a writer; applications may select a
different journal mode when their storage environment requires it.


## Unknowns

No unresolved design questions remain before implementation planning.


## Technical Notes

- The repository currently has no async command support. Existing Typer decorators wrap synchronous callbacks, so async
  command support must be handled deliberately at the Typer boundary rather than assuming Typer awaits coroutines.
- The existing settings, files, and logging features already use the XDG state home and configured application name;
  the database location follows that convention. Cache uses the separate XDG cache home.
- The project supports Python 3.12 and newer. Aiosqlite becomes a runtime dependency for this feature.
- Aiosqlite’s asynchronous API is the primary interface. Synchronous wrappers are convenience for synchronous callers,
  not a second database abstraction or an ORM.
- V1 uses pure SQL migrations. Applications choose how to load SQL text and supply it to the registry, which assigns
  monotonically increasing indices and stable identifiers. Migration API details belong in the implementation plan.
- Migrations are forward-only in v1. Checksums detect edited applied migrations, and failed migrations do not advance
  recorded schema state.
