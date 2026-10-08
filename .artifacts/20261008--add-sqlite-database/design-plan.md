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

An application packages its ordered SQL migration scripts as application resources and registers that migration source
with the database feature. Migration identifiers are unique and sortable, and the registered sequence must be strictly
increasing by identifier; the feature does not silently reorder scripts. Duplicate or out-of-order identifiers, or
unavailable migration resources, produce a feature-specific error before any migration is applied, and the attached
application command does not proceed. The same registered source is used by command attachments and database-management
commands. Opening an attached database applies pending migrations in order before the command uses the database. A new
database reaches the same current schema as an existing database after all registered migrations run.


#### AC07: Migrations are tracked and concurrency-safe

The database records applied migration identifiers and checksums. Concurrent application starts cannot apply the same
migration more than once. Modified historical migration content is detected; a checksum mismatch fails with a
migration-integrity error before any further migration is applied, and an attached application command does not proceed.


#### AC08: A failed migration does not claim success

Each migration and its tracking record commit atomically. If a migration fails, its changes and record roll back, later
migrations do not run, and the application command does not proceed. Earlier successful migrations remain recorded so
a corrected pending migration can be retried.


### Management and project integration

#### AC09: Database commands expose safe inspection and control

The optional `db` command group reports the database path without creating it, inspects database metadata without
exposing application row data, and reports applied and pending migration status without modifying the database. When
the database file does not exist, `inspect` reports that it does not exist and `status` reports every registered
migration as pending; neither creates the file. Its
`migrate` command applies pending migrations, and `reset` requires confirmation before replacing stored data and
reapplying the registered schema.


#### AC10: Errors follow typerdrive conventions

Connection, query, migration, lifecycle, and management-command failures use feature-specific errors that integrate
with typerdrive’s existing user-facing error handling and exit-code conventions.


#### AC11: Users can learn and run the feature

The feature includes new API and command reference documentation, usage examples, runnable demos, and a changelog entry.
Examples demonstrate async and synchronous access and packaged migration registration. Demos exercise database
lifecycle,
migrations, and management commands. Documentation explains async and sync usage, migration registration and failure
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

Async commands use an async manager lifecycle. The attachment integrates async command execution with Typer’s
synchronous callback boundary and reports a clear limitation if invoked from an already-running event loop. Synchronous
callers can use the wrapper API when no event loop is active. Each manager lifecycle uses either async access or
synchronous wrapper access, as specified in AC05.

Transaction scopes are serialized per manager. While one transaction is active, operations requested by other tasks wait
until it commits or rolls back; those operations cannot execute on the shared connection as part of another task's
transaction. SQLite contention that cannot be resolved through this coordination is surfaced as a useful
feature-specific error rather than mistaken for successful concurrent writes.


### Migration model

V1 uses numbered SQL migration scripts owned and packaged as application resources. The application registers an
explicitly ordered migration source with the database feature for use by both command attachments and
database-management
commands. Identifiers must be unique and sortable, and the source sequence must be strictly increasing by identifier;
invalid order is rejected rather than silently corrected. This avoids relying on a project-relative path and works in
installed applications as well as source checkouts.

The database persistently records stable migration identifiers and checksums. Concurrent application starts do not
apply the same migration more than once. If previously applied migration content has changed, migration stops with a
migration-integrity error before applying further changes, and the attached application command does not proceed. Each
migration and its recorded success are atomic: a failure leaves earlier successful migrations intact and the failed
migration eligible for retry.

Migrations are forward-only in v1; there is no command to downgrade previously applied migrations. Transaction rollback
only protects the database when an individual migration fails: that migration's partial changes are undone, while
earlier successful migrations remain applied. Applications can correct mistakes with a new forward migration or
deliberately reset data. The `db` command group provides `path`, `inspect`, `status`, `migrate`, and confirmed `reset`
operations. Normal attachment applies pending migrations before application code runs; `status` remains non-mutating,
while `migrate` makes the operation available explicitly. Reset replaces the database and applies the currently
registered migration set.

Migration sources remain separate from the files feature. They are immutable application assets, while files is
runtime-writable user data; storing migration scripts there would let runtime data alter future schema upgrades.


### Typer integration and operations

The optional `db` group follows the existing feature subcommand convention. `path` resolves and prints the configured
location without creating the database. `inspect` reports safe operational metadata, such as whether the database
exists, its SQLite and schema versions, and its journal mode, but not application records. `status` reports applied and
pending migrations without applying them. For an absent database, `inspect` reports non-existence and `status` lists all
registered migrations as pending, without creating the file. `migrate` creates the database if needed and applies
pending migrations. `reset` requires explicit confirmation before discarding the database, then restores the registered
schema.

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
- V1 uses pure SQL migrations; applications package and register their migration resources. Migration API details belong
  in the implementation plan.
- Migrations are forward-only in v1. Checksums detect edited applied migrations, and failed migrations do not advance
  recorded schema state.
