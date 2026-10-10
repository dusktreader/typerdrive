# Implementation Plan: SQLite database feature

Implement typerdrive's approved SQLite feature as an async-first, lifecycle-managed database using aiosqlite. Add
explicit sync wrappers that preserve a single connection lifecycle without nesting event loops, application-supplied SQL
migration strings with generated stable identifiers, safe management commands, context injection, and user-facing
documentation and examples.


## Goal

Add a `typerdrive.database` feature that gives each app a SQLite database at the configured XDG state location, exposes
direct SQL and transaction APIs, and applies registered application migrations before attached commands run. Support
explicit async lifecycles for long-lived work and sync commands through wrappers that reject use from a running event
loop or mixed async/sync manager access.

Integrate the feature with the project's attachment, context, error, command, packaging, documentation, example, and
demo conventions. Typer's sync callback boundary must await decorated async commands to completion and close the manager
after success, errors, or cancellation. Provide optional `db path`, `db inspect`, `db status`, `db setup`, `db migrate`,
and confirmed `db reset` commands. Do not add an ORM or application schema to typerdrive.


## Project Commands

### Update and verify dependencies

Command:

```shell
uv lock
```

Expected Output:

`uv.lock` resolves aiosqlite as a runtime dependency and remains synchronized with `pyproject.toml`.


### Run unit tests

Command:

```shell
make qa/test-unit
```

Expected Output:

All unit tests pass. This target disables coverage enforcement; use `make qa` for the combined coverage gate.


### Run integration tests

Command:

```shell
make qa/test-integration
```

Expected Output:

All CLI integration scenarios pass, including async callbacks invoked through Typer's synchronous runner.


### Run the full quality gate

Command:

```shell
make qa
```

Expected Output:

Unit and integration tests pass with the configured coverage threshold, Ruff and typos report no issues, and `ty`
reports no type errors.


### Build documentation

Command:

```shell
make docs/build
```

Expected Output:

MkDocs builds successfully with the database feature and reference pages in the navigation.


### Build distribution artifacts

Command:

```shell
uv build
```

Expected Output:

The wheel and source distribution build successfully and include the demo's packaged SQL migration resources.


## Project Standards

- [Contributing guidelines](../../CONTRIBUTING.md) for Python, dependency, documentation, and example conventions.
- [`pyproject.toml`](../../pyproject.toml) for Python 3.12+, runtime dependencies, Ruff, pytest, and uv-build settings.
- [`uv.lock`](../../uv.lock) for the resolved dependency lock.
- [`Makefile`](../../Makefile) for canonical test, lint, type-check, docs, demo, and quality commands.
- [`docs/mkdocs.yaml`](../../docs/mkdocs.yaml) for documentation source, watch paths, and navigation.
- Existing feature patterns in `src/typerdrive/{cache,files,settings,logging}` and their matching unit tests.
- Approved [SQLite design plan](design-plan.md) for scope, invariants, and acceptance criteria.


## Relevant Skills

- `execute-implementation-plan`
- `execute-implementation-task`
- `review-implementation-execution`
- `internal-review`


## Execution

### 01: Add database configuration, errors, and dependency

Add the database location, feature-specific error types, and required async SQLite dependency.


#### Acceptance Criteria

- AC01: `TyperdriveConfig.database_path` resolves to `<xdg_state_home>/<app_name>/db.sqlite`, uses the configured app
  name and XDG state home, and does not use the cache or files location.
- AC02: Database-specific base and operation errors derive from `TyperdriveError` and retain the project's user-facing
  exit-code handling.


#### Steps

1. Add a `database_path` computed field to `src/typerdrive/config.py` and cover default XDG path, custom
   `XDG_STATE_HOME`, app-name isolation, and separation from `cache_dir` and `files_dir` in `tests/unit/test_config.py`.
2. Add `src/typerdrive/database/exceptions.py` with feature-specific errors for initialization, query/transaction,
   migration/integrity, lifecycle, and management failures; assert inheritance and error-message/exit-code behavior in
   `tests/unit/database/test_exceptions.py`.
3. Add `aiosqlite` to runtime dependencies in `pyproject.toml` and run `uv lock`; keep test-only dependencies in the dev
   group.
4. Run `make qa/test-unit` and confirm new foundation tests and existing feature tests pass.


### 02: Implement the database manager lifecycle and SQL APIs

Implement the aiosqlite-backed connection owner, async SQL and transaction interfaces, WAL initialization, and guarded
synchronous wrappers.


#### Acceptance Criteria

- AC01: Async manager entry creates parent directories and creates the SQLite file if absent, opens one connection at
  the
  configured path, selects WAL by default, and closes the connection on normal exit, exception, and cancellation.
- AC02: Callers can execute parameterized SQL and retrieve rows through the async API without an ORM; SQLite and
  connection failures become database feature errors.
- AC03: A manager lifecycle permits async APIs or sync-wrapper APIs, but mixing them fails with a lifecycle error that
  identifies the supported API.
- AC04: Sync wrappers preserve one manager connection for the synchronous lifecycle, work only when no event loop is
  running, and direct callers in an active loop to the async API without nesting or blocking that loop.
- AC05: Transaction scopes serialize across tasks on one manager. Other tasks wait outside the active transaction;
  normal exit commits; exceptions and cancellation roll back; contention/failure is surfaced as a feature error.
- AC06: Applications may select another supported journal mode; invalid or failed journal-mode configuration fails
  clearly.
- AC07: A database-path-scoped cross-process lock provides shared access for manager/migration lifecycles and exclusive
  access for reset. Managers acquire shared access before opening or migrating and hold it until close. Reset attempts
  exclusive access before changing files and fails without changes if shared access is active; new managers wait while
  reset holds exclusive access.


#### Steps

1. Add failing tests in `tests/unit/database/test_manager.py` for async context entry/exit, directory creation, path,
   WAL, alternate journal mode, parameterized execution, row retrieval, lifecycle coordination acquire/release, and
   failed
   connect/query/close behavior.
2. Run `uv run pytest tests/unit/database/test_manager.py --no-cov` and confirm the lifecycle/API tests fail before
   implementation.
3. Implement `DatabaseManager` in `src/typerdrive/database/manager.py` using `aiosqlite`; keep connection creation and
   closure explicit and avoid adding schema/query abstractions. Implement the database-path-scoped cross-process lock:
   managers acquire shared access before opening/migrating and retain it through close; reset acquires exclusive access.
4. Add async execute/fetch helpers and an async transaction context manager. Coordinate access with task-aware manager
   synchronization so non-owner tasks cannot execute on a connection while another task owns a transaction.
5. Add a synchronous lifecycle and wrappers that dispatch to a manager-owned event-loop bridge for the same aiosqlite
   connection. Detect an already-running caller loop before dispatch and reject use instead of nesting `asyncio.run` or
   blocking that loop.
6. Add tests for multiple operations within one sync lifecycle, async/sync mode mixing, calls made from an active event
   loop, and lifecycle cleanup after failures; rerun the focused unit test file.
7. Test transaction commit, rollback on raised exception and cancellation, cross-task exclusion, waiting writes, and
   independent reads after completion. Add regression cases for SQLite lock/contention errors.
8. Run `make qa/test-unit` and confirm the complete unit suite passes.


#### Technical Notes

Keep the sync wrapper as a bridge to the same aiosqlite manager, not a second database implementation. Ensure
cancellation cleanup awaits rollback and connection closure before propagating cancellation. Do not allow operations
from another task to join the transaction that owns the shared connection.


### 03: Add registered SQL migrations with generated identifiers

Add an application-owned migration registry that accepts SQL text, assigns stable identifiers in registration order,
validates the complete migration sequence, and applies each migration atomically under concurrent startup.


#### Acceptance Criteria

- AC01: Client applications register each migration with a non-empty description and SQL text; the registry assigns
  sequential indices beginning at 1 and generates the stable identifier as `f"{idx:08d}{inflection.underscore(desc)}"`.
- AC02: Registration order defines migration order. Empty descriptions or SQL text fail with a migration-specific error
  before any migration is applied and prevent the attached command from proceeding.
- AC03: A new database and an existing database both reach the schema represented by the complete registered sequence;
  applied indices, generated identifiers, and content checksums are stored in a feature-owned tracking table.
- AC04: Every previously applied index must still be registered with the same generated identifier and SQL checksum.
  Removed entries, changed descriptions, or changed SQL fail with a migration-integrity error before later migrations
  run.
- AC05: Each migration's schema changes and tracking record are atomic. A failed migration leaves no partial schema or
  success record, later migrations do not run, and earlier successful records remain available for retry.
- AC06: Concurrent processes applying the same source serialize at SQLite's write boundary and record/apply each
  migration once.
- AC07: Both attachment and database-management commands use the same registered source; migrations are forward-only.


#### Steps

1. Define `MigrationRegistry` in `src/typerdrive/database/migrations.py` with `register_migration(desc: str, sql_text:
   str)`. Client code loads SQL by any chosen method and supplies the text; typerdrive does not load client files or
   invoke Python migration callbacks. Assign indices from 1 in registration order and generate IDs with
   `f"{idx:08d}{inflection.underscore(desc)}"`.
2. Add migration fixtures as SQL strings registered directly in tests. Keep any filesystem or package-resource loading
   in demo/client code, outside the typerdrive migration API.
3. Test sequential index/ID generation, empty descriptions or SQL, ordered application, fresh/existing schema
   equivalence, missing or changed applied indices, changed descriptions or SQL, failed SQL, retry, and suppression of
   subsequent migrations after failure.
4. Validate the complete registry and supplied SQL text before opening a write transaction. Compute checksums from the
   exact SQL text and verify every applied index still has the same generated ID and checksum before applying
   migrations.
5. Create the internal migration ledger and acquire a SQLite write lock before checking/applying pending records so
   concurrent startup cannot double-apply work.
6. Run each migration and its ledger insert in the same transaction. Ensure the SQL script execution path does not let
   `executescript` implicitly commit outside that transaction; on any SQL or ledger failure, explicitly roll back and
   preserve earlier committed migrations.
7. Test two managers/process-like connections applying the same migration sequence, asserting a single ledger row and
   successful final schema; include cancellation/failure cleanup.
8. Run `uv run pytest tests/unit/database/test_migrations.py --no-cov` and then `make qa/test-unit`.


#### Technical Notes

The registry accepts SQL text and does not control how the client loads it; examples may use package resources as one
option. Treat registered migrations as append-only history: add new registrations at the end and use `db reset` to clear
the database and tracking history before rebuilding from a changed migration sequence. Use checksums to detect edits to
historical SQL, not as migration identifiers.


### 04: Attach the manager and execute async commands through Typer

Integrate command attachment, typed injection, context lookup, asynchronous command awaiting, synchronous command
behavior, and error handling at Typer's synchronous callback boundary.


#### Acceptance Criteria

- AC01: `@attach_database` provides a live manager through `TyperdriveContext`, a typed command parameter, and
  `get_database_manager(ctx)`; string annotations work as they do for other attachments.
- AC02: Attaching to an absent database creates and configures the file, then applies the full migration registry before
  user code runs. Attaching to an existing database applies pending migrations. Any validation or migration failure
  prevents user code from running.
- AC03: Decorated async commands are awaited to completion, and the database remains open until completion; sync
  decorated commands remain callable with sync wrappers.
- AC04: The attachment closes the manager after command success, exception, and cancellation and preserves the original
  command result/error semantics.
- AC05: Invoking the synchronous Typer boundary from a running event loop raises an actionable database/Typer
  integration error instead of returning an unawaited coroutine or nesting an event loop.
- AC06: `handle_errors` displays failures raised after awaiting an async decorated command while preserving current sync
  exception behavior and exit codes.
- AC07: The manager is stored in `TyperdriveContext`, typed injection and lookup use `TyperdriveManager`, and the public
  manager, attachment, getter, and errors are exported from the feature package and root package.


#### Steps

1. Add failing tests in `tests/unit/database/test_attach.py` for context binding, typed manager injection, lookup
   failures, string annotations, migration-before-body ordering, async and sync commands, and cleanup on body
   failure/cancellation.
2. Add `CliRunner` tests for async callback output/result and for an exception raised after an `await`; assert the
   exception is handled with the expected message and exit code. Add an active-loop invocation test that verifies a
   clear error and no unawaited coroutine warning. Add a controlled cancellation test whose async callback cancels its
   task; assert cancellation propagates through the adapter and the manager is closed before it escapes.
3. Add the database manager field and union member to `TyperdriveContext` and `TyperdriveManager` in
   `src/typerdrive/context.py`; validate type storage and retrieval.
4. Implement `attach_database(migration_registry=...)` and `get_database_manager` in
   `src/typerdrive/database/attach.py`, following `SignatureRewriter`, `CloakingDevice`, and context conventions from
   `cache/attach.py` and `files/attach.py`.
5. Implement the synchronous callback adapter to distinguish coroutine functions from synchronous functions. Before
   opening the database, reject invocation if the calling thread already has a running event loop. For async callbacks,
   use one top-level `asyncio.run()` call to enter the async manager lifecycle, apply migrations, await the callback,
   and close the manager before returning or propagating its result, error, or cancellation. Keep synchronous callbacks
   on the separate sync-manager lifecycle and bridge; do not reuse that bridge for async callbacks.
6. Update `src/typerdrive/handle_errors.py` so an awaitable result is awaited before its exceptions are handled, without
   changing synchronous decorator behavior; test both decorator orders used by commands.
7. Export the manager, attachment, getter, and errors from `src/typerdrive/database/__init__.py` and
   `src/typerdrive/__init__.py`; preserve the package's established `__all__` and string-annotation behavior.
8. Confirm manager lifecycle mode checks and the running-loop guard are enforced consistently when command parameters or
   context helpers are used.
9. Run focused attachment/error tests, then `make qa/test-unit`.


#### Technical Notes

Typer and Click invoke ordinary callbacks synchronously; do not assume Typer awaits a returned coroutine. The async
callback adapter rejects a caller thread with a running event loop, then uses a single top-level `asyncio.run()` to own
the full async manager lifecycle and await the callback. Keep the synchronous wrapper bridge separate. Coordinate
`handle_errors` so post-await failures are handled before returning through Click, and preserve the signature Typer
inspects.


### 05: Add optional database management commands

Provide read-only inspection, explicit empty database setup, pending migration application, and confirmed reset under
the
`db` command group. Attachments continue to create the database and apply pending migrations automatically.


#### Acceptance Criteria

- AC01: `db path` prints the configured path without creating its directory or database file.
- AC02: `db inspect` reports safe SQLite/schema/journal metadata and database existence without exposing application
  rows; an absent file remains absent.
- AC03: `db status` reports applied and pending migrations without mutation; an absent file reports every registered
  migration as pending and does not create it.
- AC04: `db setup` obtains exclusive lifecycle access and creates/configures the database only when absent. It does not
  apply application migrations; when the database already exists, it makes no changes. If active managers or migrations
  prevent exclusive access, it fails without modifying files; new attachments wait while setup holds exclusivity.
- AC05: `db migrate` requires an existing database and applies pending registered migrations; it does not create the
  database when absent. It uses the same integrity checks and migration runner as attachments.
- AC06: `db reset` requires confirmation and exclusive cross-process access before deleting data or migration history.
  If an active manager or migration holds shared access, reset fails without modifying the database or sidecars. While
  reset holds exclusive access, new manager lifecycles and migrations wait; success applies the current sequence, while
  declined confirmation preserves the database.
- AC07: Management failures use feature-specific errors and existing user-facing formatting/exit-code conventions; the
  optional group follows existing `invoke_without_command=True` and `no_args_is_help=True` behavior.


#### Steps

1. Add failing command/help tests in `tests/unit/database/test_commands.py` for all six commands, group help,
   no-argument help, absent database behavior, output, exit codes, setup idempotency, migrate-before-setup rejection,
   and
   confirmation decline.
2. Implement `src/typerdrive/database/commands.py` and expose
   `add_database_subcommand(cli, migration_registry)` so the command group uses the same registry passed to
   `attach_database`; follow `cache/commands.py` conventions.
3. Implement `path` without opening a manager; keep absent-file `inspect` and `status` read-only.
4. Implement `inspect` with operational metadata only. Query SQLite version, schema version, journal mode, and safe
   existence/state metadata, never application tables or rows.
5. Implement `status` by validating the registered migration sequence and comparing it with the ledger when the file
   exists; report all registered migrations pending if absent.
6. Implement `setup` under exclusive cross-process lifecycle access. If the file is absent, create and configure the
   empty
SQLite database without invoking application migrations; if present, report it is already set up and preserve it. Fail
without changes when active shared users prevent exclusivity.
7. Implement `migrate` only for an existing database using the shared migration runner. If absent, report a feature
   error
   directing the user to `db setup` or an attached command; do not create a file.
8. Implement `reset` with the database-path-scoped cross-process lock. Retain exclusive access through deletion and
   rebuild, then invoke an internal locked migration routine that does not acquire a conflicting shared lease.
9. Test setup leaves application migrations pending and is a no-op when DB exists; verify it fails without changes when
   a manager holds shared access. Test migrate rejects absent DB and applies pending migrations after setup. Retain
   reset
   data/history and cross-process lock coverage.
10. Run `make qa/test-unit`.


### 06: Cover the complete database workflow with CLI integration tests

Exercise the attached application flow and management commands at the same Typer boundary users invoke, including
persistence between invocations and all important failure paths.


#### Acceptance Criteria

- AC01: A CLI scenario can use injected/context database access to create and retrieve app-owned rows across separate
  command invocations.
- AC02: A CLI scenario starts without a database and registers client-loaded SQL. Its first command-body assertions
  prove
  attachment created the file, enabled WAL, and applied the migration-created schema before later logic runs. Other
  cases
  reject empty descriptions or SQL, checksum changes, and failed SQL; generated IDs follow registration order.
- AC03: Async command success, raised failure, and cancellation close the manager; sync commands use the sync wrapper
  and persist results.
- AC04: Integration scenarios verify `db setup` creates an empty database without application schema, is idempotent, and
  fails without changes when a manager holds shared access. `db migrate` fails without creating an absent database, then
  applies migrations after setup; `db inspect` reports the initialized metadata.
- AC05: Successful `db reset` removes seeded application rows and old migration history, then applies a changed current
  registry. Declined reset preserves rows and migration history.
- AC06: Cross-process tests show active managers/migrations block setup or reset without changes; new attachments and
  migrations wait while setup/reset holds exclusive access.
- AC07: An async-loop boundary failure is actionable and does not leave a live connection or coroutine warning.


#### Steps

1. Add `tests/integration/features/database.feature` and `tests/integration/steps/test_database.py` following the
   existing files/cache BDD structure; share isolated XDG state fixtures from `tests/integration/conftest.py`.
2. Use a test application that loads SQL text with its own chosen source and registers it with the migration registry;
   invoke commands with `CliRunner` exactly as users invoke the CLI.
3. Add a fresh-state attachment scenario whose first command-body assertions check that the database file exists, WAL is
   active, and the migration-created table is queryable. Also cover async insert/select, synchronous access, context
   lookup, persistence across invocations, and multiple migrations.
4. Add failure scenarios for empty description or SQL registration, checksum mismatch, migration rollback/retry,
   command-body suppression, SQL errors, cleanup after callback error, and loop-boundary rejection.
5. Add database-management scenarios for non-mutating absent-file commands, migration status, and safe inspect output.
   Verify setup creates an empty database without app schema, is idempotent, and fails without changes when a manager is
   active. Verify migrate requires setup and applies the registered schema, while attachment still
   auto-creates/migrates.
   Seed rows/history; verify reset replaces both. Use separate processes to verify setup/reset lock behavior.
6. Run `make qa/test-integration`, inspect failing scenario output, and then run `make qa` to check combined coverage
   and regressions in existing features.


### 07: Document, demonstrate, and package demo assets

Publish the feature API and behavior in docs, runnable examples, demo modules, demo SQL assets, and the changelog.


#### Acceptance Criteria

- AC01: Feature documentation explains async and sync APIs, explicit async lifecycle, connection lifecycle, transaction
  serialization/rollback, path configuration, WAL selection, migration registration/checksums/failure ordering,
  automatic create-and-migrate on attachment, `db setup` creating an empty database without app schema, `db migrate`
  requiring an existing database and applying pending migrations, reset data loss, and ORM layering.
- AC02: API reference covers database attachment, manager, migration API, commands, and feature errors.
- AC03: Runnable examples demonstrate async SQL, sync wrappers, client-supplied SQL text, and database subcommand
  registration. The commands example demonstrates `db setup` leaving migrations pending and `db migrate` applying them.
  Client-selected package-resource loading may be shown as an alternative source.
- AC04: An attachment demo starts with an absent database and verifies inside the command body that the file exists, WAL
  is configured, and the migrated table is available. Database command demos show inline migration SQL, demonstrate `db
  setup` leaving migrations pending, `db migrate` applying them, and confirmed `db reset` rebuilding from the current
  registry. All demos remain selectable via `--feature`.
- AC05: Demo migration SQL is included in both wheel and source distribution and can be loaded after installation
  through `importlib.resources`.
- AC06: `CHANGELOG.md` records the feature under a new `Unreleased` section; docs navigation and feature overview link
  to the new pages.


#### Steps

1. Create `docs/source/features/database.md` modeled on the cache/files guides and `docs/source/reference/database.md`
   modeled on their reference stubs.
2. Update `docs/mkdocs.yaml` navigation, `docs/source/index.md`, and `README.md` feature lists to link to the database
   feature and reference.
3. Add `examples/database/attach.py`, `examples/database/commands.py`, and a sample client-owned SQL migration source.
   Demonstrate app-owned tables, show the client loading SQL text from its chosen source, and exercise `db setup`
   followed
   by `db migrate` to distinguish empty database creation from schema migration.
4. Add `src/typerdrive_demo/attach_database.py`, `src/typerdrive_demo/database_commands.py`, and the importable demo
   migration resource package. Show migration SQL inline in demo functions and keep the packaged SQL asset for the
   distribution check. Start the attachment demo with an absent database and assert inside the command body that the
   file
   exists, WAL is active, and the migration-created table is queryable. The command demo shows setup leaving migrations
   pending, migrate applying them, inspect reporting metadata, and confirmed reset reapplying the current registry.
   Register
   the features in `src/typerdrive_demo/main.py`.
5. Configure `pyproject.toml`/uv-build package inclusion for the demo migration `.sql` assets as needed. Verify
   resources are readable via `importlib.resources` in the built artifact, not merely from the source tree.
6. Add a concise database feature entry to `CHANGELOG.md` without changing the package version unless the release
   workflow explicitly requires it.
7. Build and inspect both distributions with `uv build`; confirm the demo SQL files exist in the wheel and source
   archive. Run the database demo in a non-interactive test mode or add tests that capture its CLI behavior.
8. Run `make docs/build` and resolve all broken references or navigation errors.


### 08: Run final validation and review the artifact set

Run the repository's complete quality gate and verify shipped resources and public API completeness.


#### Acceptance Criteria

- AC01: `make qa` passes, including tests, coverage, Ruff, typos, and `ty`.
- AC02: `make docs/build` succeeds.
- AC03: Built wheel and source distribution contain the intended demo SQL migration resources and do not depend on
  repository-relative paths.
- AC04: Public exports, docs, examples, demos, changelog, and tests cover every approved design acceptance criterion
  without introducing ORM or application-specific schema code into typerdrive.


#### Steps

1. Run `make qa` and address all test, coverage, lint, spelling, and type failures.
2. Run `make docs/build` and `uv build` after the final source and packaging changes.
3. Inspect built wheel and source distribution contents for SQL resources and verify migration resource loading from the
   installed package context.
4. Review the final diff against the approved design plan, especially error paths, cancellation, sync/async lifecycle
   exclusivity, non-mutating commands, migration preflight/order/checksum/atomicity, and reset safety.


## Unknowns

- None. The approved design records no unresolved questions; the implementation steps select concrete APIs and preserve
  its stated contracts.


## Technical Notes

- `TyperdriveConfig` already derives logs, settings, and files from `xdg_state_home()` and `app_name`; cache alone uses
  `xdg_cache_home()`. The database path follows the state-home pattern and uses the filename `db.sqlite`.
- Existing attachments use `SignatureRewriter`, `CloakingDevice`, context helper functions, typed injection, and getter
  helpers. Keep public parameter annotations and string-annotation handling compatible with those patterns.
- `handle_errors` currently assumes decorated functions return synchronously. Async command support must await the
  returned work before handling errors or finalizing the database lifecycle.
- `uv.lock` currently has no aiosqlite entry. Runtime dependencies live in `[project].dependencies`; the canonical
  verification commands are Make targets in `Makefile`.
- The test suite uses synchronous pytest tests and `CliRunner`; async unit tests can use `asyncio.run` to execute test
  coroutines without introducing an unlisted pytest async plugin.
- Validate the complete registry and supplied SQL text before applying migrations. Acquire the SQLite write lock before
  rechecking persisted migration state so concurrent processes cannot apply one generated ID twice. Client-owned SQL
  loading occurs before registration and remains outside typerdrive.
- SQL script execution must keep migration statements and ledger insertion inside one transaction. Account for
  sqlite3/aiosqlite `executescript` transaction behavior rather than assuming it preserves an open transaction.
- `db inspect` and `db status` are read-only even when the database does not exist. `db reset` is the only destructive
  command and confirmation must precede any file or sidecar removal.
