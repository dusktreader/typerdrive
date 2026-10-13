# Plan deviations

This artifact records human-directed implementation changes that intentionally diverge from the approved design and
implementation plans. The plans and their review artifacts remain unchanged.


## 2026-10-09: Use SQLite-native concurrency instead of process lock files

### User direction

The user determined that the database is local to the client application and that simultaneous application instances are
the only expected concurrency. The `portalocker` shared/exclusive lifecycle lease is overengineered for this use case.


### Implementation change

Remove `portalocker`, the `.lock` file protocol, and whole-manager lifetime leases. Use SQLite transactions, busy
handling, and WAL to coordinate concurrent application instances.


- `db setup` opens and configures the SQLite database without applying application migrations. It is idempotent for an
  existing database.
- `db migrate` uses SQLite transactions to serialize concurrent migration runs and applies pending registered
  migrations.
- `db reset` retains the database file and WAL sidecars. It performs schema and migration-history replacement inside a
  SQLite write transaction, then applies the current registry before commit. It does not unlink an open database file.
- Existing readers may finish against their SQLite snapshot while the reset transaction is active; conflicting writers
  serialize or receive SQLite's bounded busy/locking error. Tests verify no partial reset state is visible.

This replaces the planned lifecycle leases and active-manager reset rejection. Setup, migrate, attach, and reset retain
their distinct user-visible behavior.


### Validation

- Removed `portalocker`, the lock adapter and lifecycle tests; `uv lock` no longer resolves `portalocker`.
- Concurrent setup initializes one empty database; concurrent process migrations leave one ledger entry and schema.
- Reset tests cover rollback, WAL reader snapshots, write contention, and unchanged database-file identity.
- Test-first reset cases failed before implementation and passed with the transactional rebuild.
- Focused database tests: 83 passed. Lint, type checks, and `git diff --check` passed.
- Deferred full `make qa` to the orchestrator as requested.


## 2026-10-09: Extract generic async/sync bridging with AnyIO

### User direction

The user requested that the generic async/sync bridge be separated from `DatabaseManager` and that its
hand-managed event loop and thread be replaced with maintained library machinery. Keep the approved plan and review
artifacts unchanged.


### Implementation change

Add a reusable `typerdrive.async_tools` module backed by AnyIO's blocking portal. Move portal lifecycle, synchronous
portal calls, active-async-context rejection, and async execution at synchronous CLI boundaries into this module.
`DatabaseManager` keeps SQLite lifecycle and transaction ownership/isolation, while delegating sync execution to the
generic bridge. Attachments invoke async work through the active generic bridge API rather than accessing a private
manager
portal. Declare AnyIO as a direct runtime dependency.


### Validation

- Focused bridge, manager, attachment, migration, command, and error-handling tests: 91 passed.
- Ruff and `ty` checks passed; `uv lock --check` and `git diff --check` passed.
- Deferred full `make qa` to the orchestrator as requested.


## 2026-10-12: Move async context lifecycle into the generic adapter

### User direction

The user clarified that the generic adapter must own sync lifecycle around async context managers, not just bridge
individual calls. Keep AnyIO's maintained `BlockingPortal` implementation and leave approved plans and review artifacts
unchanged.


### Implementation refinement

`BlockingAsyncAdapter` owns async context entry/exit, AnyIO portal lifecycle, calls, and caller context propagation.
`DatabaseManager` delegates sync lifecycle and methods while retaining SQLite mode validation and transaction isolation.
`attach_database` uses the generic helper to await sync callbacks that return awaitables.


### Validation

- Focused async-tool, database, attachment, migration, command, error-handling, and database integration tests: 110
  passed.
- `make qa/lint`, `make qa/types`, `uv lock --check`, Ruff formatting, and `git diff --check` passed.
- Manager-source scan found no portal implementation references.
- Deferred full `make qa` as requested.


## 2026-10-12: Serialize synchronous database operations with a reentrant lock

### User direction

The user requested fewer custom sync/async transaction ownership mechanisms now that AnyIO provides the bridge. Keep
approved plans and reviews unchanged.


### Implementation change

Guard each synchronous wrapper operation with one manager-owned `threading.RLock`. `transaction_sync()` holds that lock
through begin, the caller body, and commit or rollback, allowing same-thread wrapper reentrance while making other
threads wait. A transaction state flag continues to reject nested sync transactions. Bridge operations bypass the async
operation lock; async manager transactions retain task ownership and asyncio locking. Remove the bridge's caller-thread
`ContextVar` because sync ownership no longer depends on thread identity. Preserve rollback and error reporting when
commit fails.


### Validation

- `uv run pytest tests/unit/test_async_tools.py tests/unit/database/test_manager.py --no-cov`: 35 passed.
- `make qa/lint`: passed.
- `make qa/types`: passed.
- Deferred full `make qa` as requested.
