# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## v0.9.7 - 2026-05-05
- Fixed `NameError: name 'Context' is not defined` crash on Python 3.14+ when using
  any `attach_*` decorator
  - Root cause: Python 3.14 `inspect.signature()` on a plain function bypasses
    `__signature__` and calls `get_annotations()`, which triggers the lazy
    `__annotate__` closure — evaluated in the wrong scope where `Context` is not
    defined
  - Fix: `SignatureRewriter.apply()` now also replaces `wrapper.__annotations__` with
    a pre-resolved dict matching the rewritten signature, preventing lazy evaluation

## v0.9.6 - 2026-05-04
- Introduced `SignatureRewriter.apply(wrapper)` method to encapsulate `__signature__`
  stamping in one place, replacing direct `wrapper.__signature__ = rewriter.build()`
  calls in all five `attach_*` decorators
- Uses `setattr` for `__signature__` so type checkers (`ty`, mypy) never see the
  assignment on a wrapped callable type — eliminates false-positive
  `unresolved-attribute` errors for both library internals and downstream consumers
- Removed unused `inspect.Parameter` import from `tests/unit/test_signature.py`


## v0.9.5 - 2026-05-04
- Fixed `NameError` in `attach_cache`, `attach_client`, `attach_files`, `attach_logging`
  - Caused by string annotations (`from __future__ import annotations` or Python 3.14+)
  - Now uses `get_type_hints()` instead of `func.__annotations__`
  - Consistent with existing fix in `attach_settings`
- Fixed type-checker error in `attach_settings` exposed by the annotation resolution refactor
  - Added `# type: ignore[invalid-type-form]` where `settings_model` is used in a runtime `Annotated` expression


## v0.9.4 - 2026-05-02
- Fixed the bug in show logs where characters in the output were interpreted by rich as markup


## v0.9.3 - 2026-03-26
- Added startup benchmark suite (`tests/benchmarks/test_startup.py`) measuring import-time and `--help`
  wall-clock cost across three CLI variants (baseline, settings-only, full)
- Added `src/typerdrive_benchmarks/` package with fixture CLIs used by the benchmark suite
- Added `pytest-benchmark>=5.0` dev dependency
- Added `benchmark` pytest marker; benchmark tests are excluded from normal test runs via `-m "not benchmark"`
- Added `make qa/benchmark` target
- Added Developer Guide page to the docs covering setup, quality-check targets, and benchmark usage


## v0.9.2 - 2026-03-19
- Fixed `attach_settings` crashing with `NameError` when the decorated function
  uses string annotations (i.e. `from __future__ import annotations` or Python 3.14+)
- `attach_settings` now resolves annotations with `typing.get_type_hints()` before
  comparing them against `settings_model` and `SettingsManager`, so string and
  evaluated annotations are handled identically


## v0.9.1 - 2026-03-12
- Fixed issue with binding using SecretStr settings


## v0.9.0 - 2026-03-12
- Added `SecretStr` support in settings: fields annotated with `SecretStr` are automatically masked in normal output
- Added `_dump()` helper in `SettingsManager` to correctly store `SecretStr` values as plain strings
- Added `status_message` context manager for bracketed start/success/failure output; exported from top-level package
- Added `padding` parameter to `simple_message` (default `True`) to allow suppressing blank-line padding
- Added `invoke_without_command=True, no_args_is_help=True` to all four subcommand groups (settings, cache, files, logs)
  so invoking a subcommand with no arguments shows help instead of silently exiting
- Fixed `issubclass` crash in settings `bind` and `update` commands when a field annotation is not a plain type
  (e.g. `AutoNameEnum`)
- Bumped `typer-repyt` dependency to `>=0.9.1`
- Added `auto-name-enum` as a dev dependency for tests
- Added documentation section for secret settings values


## v0.8.1 - 2026-02-11
- Removed upper bounds on all dependency version specifiers
- Bumped snick to >=3.0, py-buzz to >=8.0, typer-repyt to >=0.9.0
- Removed upper bound on requires-python
- Promoted rich from optional demo extra to a direct runtime dependency
- Updated Makefile to match project conventions


## v0.8.0 - 2025-02-01
- BREAKING CHANGE: Refactored cache from file-based to diskcache for improved performance
- Added support for caching any picklable Python object (Pydantic models, custom classes, etc.)
- Added cache features: TTL/expiration, groups, eviction policies, statistics
- Added new `FilesManager` for persistent file storage (binary, text, JSON)
- Added `files` subcommand for viewing file storage
- Updated cache commands: `show` now displays entries with TTL, `clear` supports group filtering
- Replaced mypy and basedpyright with ty
- Comprehensive documentation updates for cache and files features


## v0.7.2 - 2025-05-22
- Pinned typer-repyt version to make sure metavar is available


## v0.7.1 - 2025-05-22
- Improved nested settings support


## v0.7.0 - 2025-05-20
- Added support for nested settings models


## v0.6.1 - 2025-05-16
- Added the `list_items()` method to the cache


## v0.6.0 - 2025-05-16
- Reorganized modules a little
- Added docstrings throughout


## v0.5.3 - 2025-05-16
- Fixed python versions allowing 3.12 through 3.14


## v0.5.2 - 2025-05-12
- Fixed error when showing settings where none are set (have defaults)


## v0.5.1 - 2025-05-12
- Added `log_errors` utility function


## v0.5.0 - 2025-05-10
- Accidentally bumped minor version instead of patch


## v0.4.2 - 2025-05-10
- Fixed `app_name`


## v0.4.1 - 2025-05-09
- Fixed missing loguru dependency


## v0.4.0 - 2025-05-09
- Added `@attach_logging()` decorator and logs subcommands
- Added TyperdriveConfig to control global configuration for typerdrive specifically
- Moved `app_name` to `TyperdriveConfig`
- Added logging configuration controls to `TyperdriveConfig`
- Added a `publish` makefile target
- Fixed imports in `__all__` for root `__init__.py`
- Moved directory helpers to `dirs.py`
- Updated demos, examples, documentation, and tests


## v0.3.0 - 2025-05-08
- Added `@attach_client` and `TyperdriveClient`


## v0.2.0 - 2025-05-04
- Enabled access to settings and cache through command function parameters


## v0.1.0 - 2025-05-02
- Forked from typer-repyt and released as new package.
