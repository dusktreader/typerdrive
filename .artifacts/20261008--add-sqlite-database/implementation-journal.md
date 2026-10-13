# Implementation Journal: SQLite database feature

Execution record for the approved SQLite database implementation plan.


## Source plan

`implementation-plan.md`


## Status

**Complete**: Implementation and focused checks are complete; project-wide `make qa` is deferred to the orchestrator as
requested.


## Tasks

### Task 01: Add database configuration, errors, and dependency

#### Status

**Complete**


#### Overview

Added the XDG state-home database path, database-specific error types, and the `aiosqlite` runtime dependency.


#### Steps taken

- Added tests for configured/default state paths, application isolation, and separation from cache and files storage.
- Confirmed the initial exception test failed during collection because the database exception module did not exist.
- Implemented `database_path` and the feature exception hierarchy.
- Added `aiosqlite>=0.21` and resolved it into `uv.lock` with `uv lock`.
- Ran focused foundation tests: 22 passed.
- Ran `make qa/lint` and `make qa/types`: both passed.
- Ran `make qa/test-unit`: 258 collected, but unrelated existing settings/files tests failed due to XDG path state.


#### Files modified

- UPDATED: `pyproject.toml`
- UPDATED: `src/typerdrive/config.py`
- UPDATED: `tests/unit/test_config.py`
- CREATED: `src/typerdrive/database/exceptions.py`
- CREATED: `tests/unit/database/test_exceptions.py`
- UPDATED: `uv.lock`


#### Acceptance criteria validation


#### Satisfied AC01: Database path follows XDG state home and is isolated

`tests/unit/test_config.py` passes for the default path, custom `XDG_STATE_HOME`, app-name isolation, and distinct
cache/files locations.


#### Satisfied AC02: Database errors derive from `TyperdriveError`

`tests/unit/database/test_exceptions.py` passes for inheritance, message preservation, and the standard general-error
exit code.


#### Additional notes

The shell exports a custom `XDG_STATE_HOME`, which bypasses existing temporary-`HOME` test fixtures. Rerunning the full
unit suite with `env -u XDG_STATE_HOME` passed. `make qa` remains excluded by the user request for orchestrator-only
final QA.


### Task 02: Implement database manager lifecycle and SQL APIs

#### Status

**Complete**


#### Overview

Implemented the aiosqlite connection manager, async SQL/transaction methods, guarded synchronous wrappers, WAL
configuration, and database-path-scoped shared file locking.


#### Steps taken

- Added failing tests for async/sync lifecycle behavior, SQL methods, transaction rollback/serialization, journal modes,
  and initialization/query errors.
- Implemented shared cross-process locking, a dedicated synchronous event-loop bridge, and task-aware transaction
  serialization.
- Added cancellation rollback and sync/async API coordination tests.
- Ran `tests/unit/database/test_manager.py`: 18 passed after edge-case coverage was completed.
- Ran `env -u XDG_STATE_HOME make qa/test-unit`: 279 passed.
- Ran `make qa/lint` and `make qa/types`: both passed after fixes.


#### Files modified

- CREATED: `src/typerdrive/database/locking.py`
- CREATED: `src/typerdrive/database/manager.py`
- CREATED: `tests/unit/database/test_manager.py`


#### Acceptance criteria validation


#### Satisfied AC01: Async lifecycle opens and closes one WAL connection

`tests/unit/database/test_manager.py::test_async_lifecycle_creates_parent_and_uses_wal` passes.


#### Satisfied AC02: Async SQL supports parameters and wraps failures

`test_async_sql_methods_parameterize_and_fetch_rows` and `test_query_failure_is_wrapped` pass.


#### Satisfied AC03: Lifecycle prevents mixed API use

`test_async_and_sync_apis_cannot_be_mixed` and `test_async_api_cannot_join_sync_lifecycle` pass.


#### Satisfied AC04: Sync wrappers bridge one connection without nesting loops

`test_sync_lifecycle_keeps_one_connection` and `test_sync_calls_reject_running_event_loop` pass.


#### Satisfied AC05: Transactions serialize and roll back on exception/cancellation

`test_non_owner_waits_until_transaction_finishes`, `test_transaction_commits_and_rolls_back`, and
`test_cancelled_transaction_rolls_back_and_closes` pass.


#### Satisfied AC06: Supported journal modes are validated

`test_alternate_journal_mode` and `test_invalid_journal_mode_fails_initialization` pass.


#### Satisfied AC07: Shared manager access uses a path-scoped cross-process lock

`DatabaseManager._open` acquires the shared `DatabaseFileLock` before opening and releases it only after close;
concurrent manager initialization/migrations pass in `test_simultaneous_migration_runs_apply_once`.


### Task 03: Add registered SQL migrations with generated identifiers

#### Status

**Complete**


#### Overview

Implemented the ordered SQL migration registry, stable generated identifiers and checksums, integrity preflight, and
per-migration transactional application with SQLite write-lock serialization.


#### Steps taken

- Added registration, ordered-ID, invalid-input, checksum/history, rollback/retry, and concurrent-run tests.
- Implemented exact SQL checksum tracking and statement parsing without `executescript` implicit commits.
- Applied migrations within `BEGIN IMMEDIATE` transactions and rechecked the complete ledger under each write lock.
- Ran `tests/unit/database/test_migrations.py`: 9 passed after integrity-gap coverage was added.
- Ran `make qa/lint`, `make qa/types`, and `env -u XDG_STATE_HOME make qa/test-unit`: all passed, with 279 unit tests.


#### Files modified

- CREATED: `src/typerdrive/database/migrations.py`
- CREATED: `tests/unit/database/test_migrations.py`
- UPDATED: `src/typerdrive/database/manager.py`


#### Acceptance criteria validation


#### Satisfied AC01: Ordered migration registration generates stable IDs

`test_registration_assigns_ordered_stable_identifiers` passes against the specified `inflection.underscore` formula.


#### Satisfied AC02: Empty registration fails before migration effects

`test_empty_registration_fails_before_database_changes` passes for empty description and SQL inputs.


#### Satisfied AC03: Fresh database reaches current schema and tracks checksums

`test_applies_migrations_in_order_and_tracks_checksums` verifies schema, index, IDs, and SHA-256 checksums.


#### Satisfied AC04: Historical changes fail integrity checks

`test_changed_description_or_sql_fails_before_later_migration` confirms later schema is not applied after identity
drift.


#### Satisfied AC05: Migration and ledger changes are atomic

`test_failed_migration_rolls_back_and_can_retry` confirms the failed DDL is rolled back, previous history remains, and
corrected SQL can be retried.


#### Satisfied AC06: Concurrent migration runs apply once

`test_simultaneous_migration_runs_apply_once` verifies concurrent manager startup produces one ledger record.


#### Satisfied AC07: Attachment and management commands share the registry; migrations are forward-only

`attach_database` and `add_database_subcommand` will receive the same `MigrationRegistry`; the API only applies
registered migrations forward. Integration tests are recorded under Tasks 04 through 06.


### Task 04: Attach the manager and execute async commands through Typer

#### Status

**Complete**


#### Overview

Integrated database context storage, typed manager injection, sync/async command lifecycles, migration-before-callback
execution, async error handling, and root/feature exports.


#### Steps taken

- Added failing Typer tests for sync and async injection, context lookup, migration ordering, string annotations,
  cleanup,
  cancellation, running-loop rejection, and both `handle_errors` decorator orders.
- Added the manager union member and field to `TyperdriveContext`.
- Implemented `attach_database` with a single `asyncio.run` for async commands and the manager-owned bridge for sync
  commands.
- Updated `handle_errors` to await async decorated callbacks before handling post-await failures.
- Exported the public attachment, manager, migration API, getter, and database errors.
- Ran focused attachment and error tests: 24 passed.
- Ran `env -u XDG_STATE_HOME make qa/test-unit`: 288 passed.
- Ran `make qa/lint` and `make qa/types`: both passed.


#### Files modified

- UPDATED: `src/typerdrive/context.py`
- CREATED: `src/typerdrive/database/attach.py`
- CREATED: `src/typerdrive/database/__init__.py`
- UPDATED: `src/typerdrive/handle_errors.py`
- UPDATED: `src/typerdrive/__init__.py`
- CREATED: `tests/unit/database/test_attach.py`


#### Acceptance criteria validation


#### Satisfied AC01: Manager is available in context and typed injection

`test_sync_command_injects_manager_and_context_lookup` and `test_manager_injection_preserves_string_annotations` pass.


#### Satisfied AC02: Migrations run before application callback

`test_migration_failure_prevents_command_body` confirms failed migration prevents entry into user code.


#### Satisfied AC03: Async and sync commands work through Typer

`test_async_command_is_awaited_and_database_stays_open` and `test_sync_command_injects_manager_and_context_lookup` pass.


#### Satisfied AC04: Database closes on completion, failure, and cancellation

`test_manager_is_closed_when_async_callback_fails` and `test_cancelled_async_command_closes_manager` verify cleanup.


#### Satisfied AC05: Running-loop invocation is rejected

`test_async_boundary_rejects_running_loop` observes an actionable `DatabaseLifecycleError` without coroutine leakage.


#### Satisfied AC06: `handle_errors` catches failures after `await`

`test_handle_errors_handles_async_exception_after_await_in_both_orders` passes with exit code 1 for each decorator
order.


#### Satisfied AC07: Context and public exports use the feature manager

`TyperdriveContext.database_manager`, `TyperdriveManager`, `src/typerdrive/database/__init__.py`, and root exports
expose
the database API.


### Task 05: Add optional database management commands

#### Status

**Complete**


#### Overview

Implemented all six optional `db` commands. Setup creates an empty WAL-configured database under exclusive lifecycle
access, while migrate applies registered SQL only to an existing database under shared lifecycle access.


#### Steps taken

- Added failing tests for setup, migrate, lifecycle exclusion/waiting, empty setup schema, no-op preservation, migration
  ledger application, status transitions, and help registration.
- Confirmed the new command tests failed because `setup` and `migrate` were not registered.
- Implemented exclusive-lock setup without app migrations and shared-lock migration using the existing registry runner.
- Preserved path, inspect, status, reset, confirmation, and group help behaviors.
- Ran focused command, manager, and migration tests: 48 passed.
- Ran `make qa/lint` and `make qa/types`: both passed.


#### Files modified

- UPDATED: `src/typerdrive/database/commands.py`
- UPDATED: `tests/unit/database/test_commands.py`
- UPDATED: `.artifacts/20261008--add-sqlite-database/implementation-journal.md`


#### Acceptance criteria validation


#### Satisfied AC01: Path output does not create the database

`test_path_does_not_create_parent_or_database` verifies both the database and parent remain absent.


#### Satisfied AC02: Inspect reports safe metadata only

`test_absent_inspect_and_status_are_read_only` and `test_inspect_reports_metadata_without_application_rows` verify
read-only absent-file behavior and metadata-only output.


#### Satisfied AC03: Status reports pending and applied migrations without mutation

`test_status_reports_migrations_pending_after_setup_and_applied_after_migrate` verifies status before and after applying
registered migrations. The absent-file status test confirms pending output without file creation.


#### Satisfied AC04: Setup is exclusive, empty on creation, and preserves existing databases

`test_setup_creates_empty_database_without_application_schema` verifies WAL and no application or ledger tables;
`test_setup_existing_database_preserves_schema_and_data` confirms existing data and journal mode remain unchanged.
`test_setup_fails_without_changes_when_shared_lifecycle_is_active` verifies contention rejection, and
`test_new_manager_waits_while_exclusive_setup_lock_is_held` verifies new attachments wait for exclusivity to end.


#### Satisfied AC05: Migrate requires an existing database and uses registered migrations

`test_migrate_rejects_absent_database_without_creating_it` verifies actionable failure without database creation;
`test_migrate_after_setup_applies_registered_schema_and_ledger` verifies schema and ledger application.


#### Satisfied AC06: Reset retains confirmation and exclusive rebuild behavior

`test_reset_requires_confirmation_and_rebuilds_current_schema`, `test_declined_reset_preserves_rows_and_history`, and
`test_active_shared_lock_blocks_reset_without_modifying_database` pass.


#### Satisfied AC07: Errors and optional-group behavior follow project conventions

Management failures use `handle_errors`; `test_group_help_and_no_argument_help` verifies no-argument help and that
`setup` and `migrate` appear in the command help.


### Task 06: Cover the database workflow with CLI integration tests

#### Status

**Complete**


#### Overview

Expanded the CLI BDD suite to prove fresh attachment initialization before callback logic, management command behavior,
migration retry, error cleanup, and shared/exclusive cross-process lock behavior.


#### Steps taken

- Kept each scenario isolated under its temporary XDG state directory and invoked user-facing commands through
  `CliRunner`.
- Asserted in the first operation of the fresh attached callback that the database file exists, WAL is active, and the
  migration-created table is queryable.
- Covered async/sync persistence, invalid descriptions and SQL, checksum mismatch, failed SQL rollback/retry, and
  migration identifier order.
- Covered absent-file path/inspect/status behavior, empty idempotent setup, absent migrate rejection, migrate after
  setup,
  reset/rebuild, declined reset preservation, and setup/reset lock conflicts.
- Used separate processes to verify an attached command and `db migrate` wait for exclusive access; tested async
  failure,
  cancellation, and active-loop rejection.
- Ran `tests/integration/steps/test_database.py --no-cov`: 18 passed.
- Ran `env -u XDG_STATE_HOME make qa/test-integration`: 44 passed across the integration suite.
- Ran `make qa/lint` and `make qa/types`: both passed.


#### Files modified

- UPDATED: `tests/integration/conftest.py`
- CREATED: `tests/integration/features/database.feature`
- CREATED: `tests/integration/steps/test_database.py`


#### Acceptance criteria validation


#### Satisfied AC01: CLI persistence works through injection and context

Async and sync BDD scenarios persist rows across separate `CliRunner` invocations and verify the manager is bound to
`TyperdriveContext`.


#### Satisfied AC02: Fresh attachment and migration validation are covered

The fresh-state callback's first operations assert file existence, WAL, and the migrated table. BDD scenarios reject
empty
descriptions and SQL, reject checksum drift, roll back a failed migration, retry it, and compare recorded IDs to
registry
order.


#### Satisfied AC03: Async and sync command lifecycles are covered

BDD scenarios verify async/sync persistence, manager closure after an async command error, and manager closure after
cancellation.


#### Satisfied AC04: Management commands work end-to-end

Scenarios verify read-only absent-file commands, setup idempotency and empty schema, migrate's absent-file failure and
post-setup application, and inspect/status metadata.


#### Satisfied AC05: Reset removes old schema and rebuilds current schema

The reset scenario verifies the old table is gone, the new table is present, and the migration ledger contains only the
current registry entry and checksum. Declining reset preserves the application row and migration history.


#### Satisfied AC06: Cross-process lock behavior is safe

A live manager blocks setup and reset without data loss. Separate processes show attachments and migrations waiting
until exclusive access is released.


#### Satisfied AC07: Running-loop invocation fails actionably

An attached command invoked from an active loop returns the expected lifecycle error, does not enter the callback, and
leaves the database file absent.


### Task 07: Document, demonstrate, and package database assets

#### Status

**Complete**


#### Overview

Aligned feature and API docs with attachment/setup/migrate behavior, added an executable setup-to-migrate example,
and expanded database demos with fresh-file proof and management lifecycle coverage.


#### Steps taken

- Documented async/sync APIs, explicit lifecycles, transaction behavior, storage configuration, WAL, migration
  checksums/failure semantics, command distinctions, reset data loss, and ORM layering.
- Clarified in both feature and API reference docs that attachment auto-creates and migrates, `db setup` creates an
  empty
  database only, and `db migrate` requires an existing database.
- Added client-owned SQL loading and a runnable `migration-workflow` example that proves setup leaves migrations pending
  and migrate applies them.
- Updated the attachment demo to start with an absent file and visibly verify existence, WAL, and the migrated table
  inside the callback before inserting data.
- Added inline migration SQL to each database demo function; the management demo shows setup/status, migration, inspect,
  and confirmed reset/rebuild from the current registry.
- Kept database demo functions selectable; manually ran `typerdrive-demo --feature attach_database` and
  `typerdrive-demo --feature database_commands` with affirmative demo prompts. All six demos completed with exit code 0;
  the inspect demo showed SQLite version, schema version, and WAL after setup/migration.
- Preserved the packaged SQL migration resource and prior wheel/sdist verification through `importlib.resources`.
- Ran `make docs/build`: succeeded; MkDocs reported the existing broken client API anchor.
- Ran `make qa/lint` and `make qa/types`: both passed.
- Did not run `make qa`; final QA remains with the orchestrator.


#### Files modified

- CREATED: `docs/source/features/database.md`
- CREATED: `docs/source/reference/database.md`
- UPDATED: `docs/mkdocs.yaml`
- UPDATED: `docs/source/index.md`
- UPDATED: `README.md`
- UPDATED: `CHANGELOG.md`
- CREATED: `examples/database/attach.py`
- CREATED: `examples/database/commands.py`
- CREATED: `examples/database/migrations/0001_create_items.sql`
- UPDATED: `pyproject.toml`
- UPDATED: `src/typerdrive_demo/main.py`
- UPDATED: `src/typerdrive_demo/helpers.py`
- CREATED: `src/typerdrive_demo/attach_database.py`
- CREATED: `src/typerdrive_demo/database_commands.py`
- CREATED: `src/typerdrive_demo/database_migrations/__init__.py`
- CREATED: `src/typerdrive_demo/database_migrations/00000001create_demo_items.sql`


#### Acceptance criteria validation


#### Satisfied AC01: Feature documentation explains API behavior and command distinctions

`docs/source/features/database.md` explains async/sync APIs, lifecycles, transactions, path/WAL, migration integrity,
automatic attachment migration, empty setup, existing-database-only migrate, reset data loss, and ORM layering.


#### Satisfied AC02: API reference covers the database surface

`docs/source/reference/database.md` includes the attachment/setup/migrate distinction and API directives for database
attachment, manager, migrations, commands, and errors. `make docs/build` succeeds.


#### Satisfied AC03: Runnable examples demonstrate SQL and management behavior

The attachment example loads client-owned SQL and demonstrates async/sync SQL. The commands example's
`migration-workflow` verifies pending status after setup and applied status after migrate; its smoke test asserts
success.


#### Satisfied AC04: Database demos prove attachment and management behavior

Manually running both `typerdrive-demo --feature attach_database` and `typerdrive-demo --feature database_commands`
shows the attach callback verifying a fresh file, WAL, and migrated table. The management demos show pending/applied
transitions, inspect metadata, and confirmed reset rebuilding the current schema. All six demo functions completed with
exit code 0.


#### Satisfied AC05: Packaged SQL resources remain loadable

The demo SQL resource remains included in both distributions; prior archive checks and an isolated wheel environment
verified `importlib.resources` loading.


#### Satisfied AC06: Release notes and navigation remain aligned

`CHANGELOG.md` has the Unreleased SQLite entry; MkDocs navigation, feature overview, and README link to the feature and
reference pages.


#### Additional notes

MkDocs still reports the existing unresolved client API anchor in `features/client.md`.


### Task 08: Run final validation and review the artifact set

#### Status

**Complete**


#### Overview

Reviewed the implementation against the approved design and verified unit, integration, lint, type, docs, build, and
resource-packaging checks. The project-wide quality gate remains assigned to the orchestrator.


#### Steps taken

- Ran `env -u XDG_STATE_HOME make qa/test-unit`: 305 passed.
- Ran `env -u XDG_STATE_HOME make qa/test-integration`: 35 passed.
- Ran `make qa/lint` and `make qa/types`: both passed.
- Ran `make docs/build`: succeeded, with an existing broken client API anchor warning.
- Ran `uv build`; confirmed the demo SQL resource is present in the wheel and source distribution.
- Loaded the packaged migration using `importlib.resources` from an isolated environment with the built wheel installed.
- Reviewed the final worktree diff, verified `git diff --check`, and confirmed the design and implementation plans were
  untouched.
- Did not run `make qa`; the user explicitly reserved the project-wide quality gate for the orchestrator.


#### Files modified

- UPDATED: `src/typerdrive/database/manager.py`
- UPDATED: `src/typerdrive/database/migrations.py`
- UPDATED: `tests/unit/database/test_manager.py`
- UPDATED: `tests/unit/database/test_migrations.py`


#### Acceptance criteria validation


#### Unsatisfied AC01: Project-wide `make qa` passes

Deferred as explicitly requested. Focused unit and integration targets, lint, and type checks pass; the combined
coverage
gate has not been run and remains for the orchestrator.


#### Satisfied AC02: Documentation builds

`make docs/build` succeeds. MkDocs reports the existing unresolved API anchor in `features/client.md`.


#### Satisfied AC03: Built distributions contain SQL resources

The wheel and source distribution both contain `typerdrive_demo/database_migrations/00000001create_demo_items.sql`;
the wheel-installed resource loads through `importlib.resources`.


#### Satisfied AC04: Approved feature scope and artifact set are represented

Root and feature exports, tests, docs, examples, demos, and changelog cover the approved database API. Application
schema
is confined to example/demo SQL; no ORM or application schema was added to `typerdrive`.


#### Additional notes

The user-requested final `make qa` remains the only deferred plan check. `uv build` emits the repository's existing
warning
that `uv-build` has no upper version bound.


----

## Post-review fixes

Resolved review findings C01 and S01–S05. Left T01's test file, both approved plans, and the review artifact unchanged.


### Steps taken

- Added deferred-foreign-key commit-failure coverage and wrapped commit errors; rollback failures retain both
  exceptions.
- Isolated synchronous transaction ownership by caller thread; added cross-thread commit/rollback tests and concurrent
  transaction rejection coverage.
- Replaced `fcntl` with the portable `portalocker` dependency, updated `uv.lock`, and tested shared/exclusive behavior
  and
  package import without direct `fcntl` imports.
- Awaited sync-callable-produced awaitables at the attached command boundary; tested post-await error handling and
  finalization.
- Added sync attached commands to the runnable database example and a CLI smoke test.
- Added removed-migration integrity coverage by applying two migrations, then retrying with only the first registered.
- Ran focused unit tests across manager, attachment, locking, migrations, and example areas: 49 passed.
- Ran `make qa/lint` and `make qa/types`: both passed. Did not run `make qa`; final QA remains with the orchestrator.


### Files modified

- UPDATED: `pyproject.toml`
- UPDATED: `uv.lock`
- UPDATED: `src/typerdrive/database/locking.py`
- UPDATED: `src/typerdrive/database/manager.py`
- UPDATED: `src/typerdrive/database/attach.py`
- UPDATED: `tests/unit/database/test_manager.py`
- UPDATED: `tests/unit/database/test_attach.py`
- CREATED: `tests/unit/database/test_locking.py`
- UPDATED: `tests/unit/database/test_migrations.py`
- UPDATED: `examples/database/attach.py`
- UPDATED: `tests/unit/test_demo_database.py`
- UPDATED: `.artifacts/20261008--add-sqlite-database/implementation-journal.md`


### Acceptance criteria validation

- **Satisfied C01**: Deferred-constraint commit failure rolls back the row; combined commit/rollback exceptions remain
  inspectable in the wrapped error.
- **Satisfied S01**: Non-owner caller threads wait until a synchronous transaction commits or rolls back.
- **Satisfied S02**: The package and lock adapter load and operate without a direct `fcntl` import; lock contention
  tests
  cover shared and exclusive access.
- **Satisfied S03**: Typer awaits a coroutine returned by a sync callable; post-await failures are handled and
  finalizers
  run.
- **Satisfied S04**: The example's sync attached commands pass a `CliRunner` smoke test.
- **Satisfied S05**: The removed-applied-migration branch raises before the schema changes.

