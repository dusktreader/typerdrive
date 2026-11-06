# Execution journal: Recursive FilesManager listing

A journal covering execution of the approved implementation plan and its four ordered tasks.


## Source plan

`.artifacts/20261105--feat--add-recursive-filesmanager-listing/implementation-plan.md`


## Status

Complete


## Tasks

### Task 01: Reject symlinks in explicitly addressed file keys

#### Status

Complete


#### Overview

`resolve_path` now rejects symlink components below the configured store before resolving paths. The configured root may
still be a symlink, while file, directory, and broken links below it are rejected for manager operations.


#### Steps taken

- Added failing manager tests for file, directory, and broken symlink components and for read, write, delete, and list
  operations.
- Added a configured-symlink-root compatibility test.
- Updated `resolve_path` to inspect key components, then retain resolved containment and root-equality checks.
- Confirmed the manager tests failed before implementation and passed afterward.


#### Files modified

- UPDATED: `src/typerdrive/files/manager.py`
- UPDATED: `tests/unit/files/test_manager.py`


#### Acceptance criteria validation


#### Satisfied AC01: Reject symlink components in resolve_path

`test_resolve_path__rejects_symlink_components` covers file, directory, and broken links and verifies `FilesError`.


#### Satisfied AC02: Reject symlinks for manager operations without modifying targets

`test_file_operations__reject_symlink_paths` covers store, load, delete, and list against internal, external, and broken
links. It verifies target existence and bytes remain unchanged and the link remains present.


#### Satisfied AC03: Allow a symlinked configured root

`test_resolve_path__supports_symlinked_configured_root` resolves, stores, and loads a normal key through a configured
root symlink and verifies the returned path is inside the target directory.


#### Satisfied AC04: Preserve symlink-free storage and deletion behavior

`test_delete__removes_empty_parent_and_preserves_storage_root` verifies the deleted file and its empty parent are
removed, the returned path remains resolved, and the configured storage root remains. Existing manager tests also cover
byte, text, JSON, and sibling preservation.


### Task 02: Add recursive and missing-tolerant listing

#### Status

Complete


#### Overview

`list_items` accepts explicit `recursive` and `missing_ok` options, preserves immediate basename results by default, and
returns storage-root-relative keys for recursive requests. Missing paths, root aliases, non-directories, read failures,
and symlinks follow the approved error and omission rules.


#### Steps taken

- Added manager tests for default and recursive behavior, key usability, missing directories, root aliases,
  non-directories, symlink entries, requested-directory read failures, nested read failures, and exception causes.
- Confirmed the new listing tests failed against the original one-argument method.
- Implemented recursive traversal that omits symlinks, accumulates all results before returning, and wraps read failures
  while preserving their causes.
- Confirmed focused manager tests pass.


#### Files modified

- UPDATED: `src/typerdrive/files/manager.py`
- UPDATED: `tests/unit/files/test_manager.py`


#### Acceptance criteria validation


#### Satisfied AC01: Preserve immediate-only default results

`test_list_items__default_is_immediate_only` verifies the default returns only the direct file name.


#### Satisfied AC02: Return usable storage-root-relative recursive keys

`test_list_items__recursive_returns_storage_root_relative_keys` verifies keys from a directory and a nested requested
directory, and confirms each key resolves to a file.


#### Satisfied AC03: Make missing-directory handling optional

`test_list_items__missing_ok` verifies missing directories return `[]` for both recursive values. The existing
`test_list_items__raises_error_if_path_does_not_exist` verifies the default remains strict.


#### Satisfied AC04: Reject non-directories with either missing option

`test_list_items__non_directory_is_rejected_with_missing_ok` and
`test_list_items__raises_error_if_path_is_not_a_directory` verify non-directory paths raise `FilesError`.


#### Satisfied AC05: Wrap read failures and return no partial results

`test_list_items__requested_read_failure_is_wrapped_with_cause` and
`test_list_items__nested_read_failure_returns_no_partial_results` verify `FilesError` retains the filesystem cause.


#### Satisfied AC06: Omit symlinks without traversal

`test_list_items__omits_symlink_entries_and_does_not_follow_directories` verifies both listing modes omit linked files
and do not expose the external target file.


#### Satisfied AC07: Reject configured-root aliases

`test_list_items__root_aliases_are_rejected` and `test_list_items__root_aliases_are_rejected_through_symlinked_root`
check `.`, `subdirectory/..`, the configured root, and its resolved target with both recursion modes and
`missing_ok=True`, for normal and symlinked configured roots.


#### Satisfied AC08: Leave ordering unspecified

No ordering assertion or ordering guarantee was added; tests compare result sets where order is unspecified.


### Task 03: Filter symlinks only in the FilesManager directory display

#### Status

Complete


#### Overview

The shared renderer omits symlinks from every display. `attach_files(show=True)` uses the same default as logging.
`clear_directory` unlinks nested symlink entries instead of traversing their targets and permits a symlink as its root
path.


#### Steps taken

- Added separate symlink-free and symlink-containing `files show` scenarios with title, root label, entries, counts,
  bytes, and omitted target assertions.
- Changed the `LoggingManager.audit` test to verify links and linked contents are omitted from its display.
- Removed the caller-selectable filter so `render_directory` and `show_directory` always omit symlink entries.
- Updated `clear_directory` to unlink nested symlink entries without following their targets while retaining support for
  a symlink root.
- Verified display and clearing behavior with focused unit and Files CLI tests.


#### Files modified

- UPDATED: `src/typerdrive/dirs.py`
- UPDATED: `src/typerdrive/files/attach.py`
- UPDATED: `tests/unit/test_dirs.py`
- UPDATED: `tests/integration/features/files.feature`
- UPDATED: `tests/integration/steps/test_files.py`


#### Acceptance criteria validation


#### Satisfied AC01: Preserve ordinary FilesManager display

The `Files show command displays stored files` scenario checks the title, configured root label, root and nested
entries, and `Storing 16 Bytes in 2 files`.


#### Satisfied AC02: Omit symlinks from FilesManager display

The `Files show command omits symlinks` scenario checks the same ordinary display and count, and verifies linked names
and the external target-only file do not appear.


#### Unsatisfied AC03: Preserve logging display behavior

The human-directed change intentionally replaces this approved criterion: `test_logging_audit__omits_symlink_display`
verifies logging omits both link names and linked contents and reports `Storing 4 Bytes in 1 files`.


#### Additional notes

The renderer implementation preceded the original display assertions, so Task 03 did not follow the plan's test-first
ordering. A later human-directed change also superseded AC03 and made symlink omission unconditional across displays.
Both deviations are recorded in `plan-deviations.md`.


### Task 04: Document listing and symlink behavior

#### Status

Complete


#### Overview

The public `list_items` docstring and Files API reference describe both options, result shapes, missing and read errors,
symlink handling, and the root-listing restriction.


#### Steps taken

- Updated the public method docstring with parameter behavior and raised conditions.
- Added a usage example and compatibility boundaries to the Files API reference.
- Formatted changed Python files with Ruff and the Markdown page with `dt format markdown`.
- Built the documentation successfully and verified the API reference includes the public method signature.


#### Files modified

- UPDATED: `src/typerdrive/files/manager.py`
- UPDATED: `docs/source/reference/files.md`


#### Acceptance criteria validation


#### Satisfied AC01: Document default and recursive return shapes

`docs/source/reference/files.md` explains immediate names by default and storage-root-relative recursive keys; the
public docstring is on `src/typerdrive/files/manager.py`.


#### Satisfied AC02: Document missing, error, symlink, and root boundaries

The Files API reference states `missing_ok` behavior, non-directory and unreadable errors, symlink omission and
rejection, and root-listing prohibition.


#### Satisfied AC03: Build the generated Files API reference

`make docs/build` succeeded. MkDocs processed `reference/files.md` and the generated API reference includes the updated
`FilesManager.list_items` signature and docstring.


#### Additional notes

Final verification passed: 440 tests, 93.41% coverage, Ruff, typos, and `ty` via `make qa`; documentation built with
`make docs/build`. The test run emitted 62 ResourceWarnings from database/cache test cleanup. MkDocs reported two broken
links in `config.md` and one missing anchor in `features/client.md`.


## Code-review resolution

The review in `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-review--feature--01.md`
identified C01 (empty-parent cleanup lacked a regression test) and S01 (missing `missing_ok=True` symlink and
symlinked-root alias coverage lacked tests).

- Added `test_delete__removes_empty_parent_and_preserves_storage_root` for C01.
- Added `test_list_items__missing_ok_rejects_symlink_paths` for broken and intermediate links.
- Added `test_list_items__root_aliases_are_rejected_through_symlinked_root` for configured and resolved root aliases in
  both recursion modes.
- Ran `uv run pytest tests/unit/files/test_manager.py tests/unit/test_dirs.py --no-cov`: 58 passed.

The review findings were coverage gaps; focused tests found no implementation defect, so no production code change was
needed.


## Human-directed changes

The human requested removing caller-selectable symlink filtering and applying omission to every directory display,
including `LoggingManager.audit`. The human's reason: the logging feature need not follow links. The request also
requires symlink-safe directory clearing.

This intentionally departs from approved design-plan AC09 and implementation-plan Task 03 AC03, which preserved
logging's symlink-following display. The configured-root symlink exception for FilesManager remains unchanged and is
covered by `test_resolve_path__supports_symlinked_configured_root`.

- Removed `exclude_symlinks` from `render_directory` and `show_directory`; all displayed symlink entries are omitted.
- Simplified the FilesManager display call and updated the logging audit expectation to one ordinary file and four
  bytes.
- Updated `clear_directory` to unlink nested file, directory, dangling, and cyclic symlink entries without traversing
  them. It accepts a symlink as the explicitly supplied root path.
- Updated the `clear_directory` docstring so the generated base-module reference documents the behavior.

Files changed: `src/typerdrive/dirs.py`, `src/typerdrive/files/attach.py`, and `tests/unit/test_dirs.py`. The production
change is documented in `plan-deviations.md`.


### Correction: preserve symlinked root behavior

The human clarified that the root-rejection guard was unwanted: an explicitly supplied symlinked directory path must
retain its prior behavior and clear the directory it designates. Removed the guard and replaced the rejection test with
`test_clear_directory__follows_symlinked_root_without_following_nested_links`, which verifies the root target is cleared
and nested symlink targets remain untouched. Nested links are still unlinked rather than traversed.

Focused verification passed: `uv run pytest tests/unit/test_dirs.py tests/unit/files/test_manager.py --no-cov
tests/integration/steps/test_files.py --no-cov` collected 69 tests and passed. `make qa` passed with 440 tests, 93.41%
coverage, Ruff, typos, and `ty`; `make docs/build` succeeded. The latest QA run emitted 57 ResourceWarnings, and MkDocs
reported two broken-link warnings and one missing-anchor warning in unchanged pages.

Symlink checks are not race-proof against concurrent filesystem changes, matching the approved design's stated limit.


## Review iteration 03: Investigate the settings test failure

The review in `execution-review--feature--03.md` reported `test_handle_errors__no_conflict_with_attach_settings`
receiving `hutt` instead of its default `jawa`, and stopped because `make qa` failed.

The failure is unrelated to the FilesManager feature. The test at `tests/unit/test_handle_errors.py:42-55` attaches a
settings model whose default is `jawa`. `SettingsManager` reads existing JSON from `config.settings_path` before
constructing that model (`src/typerdrive/settings/manager.py:46-57`). The root test fixture sets `app_name="test"` but
does not isolate `state_home` (`tests/conftest.py:9-14`); the temporary settings-path fixture is scoped to
`tests/unit/settings/`, not this test (`tests/unit/settings/conftest.py:9-23`). Thus, a persisted `settings.json` with
`name: "hutt"` at the ambient XDG state path overrides the test default. The review's observed value is consistent with
that input; no feature code participates in this settings load.

Verification in this worktree:

- `uv run pytest
  tests/unit/test_handle_errors.py::TestHandleErrors::test_handle_errors__no_conflict_with_attach_settings --no-cov`: 1
  passed.
- `make qa`: passed; 440 tests, 93.41% coverage, Ruff, typos, and type checks passed. The run emitted 61
  ResourceWarnings.

The reported failure was not reproduced in the focused test or the full quality gate. No feature-caused regression was
found, and no unrelated test or settings code was changed. The evidence and commands are recorded in
`plan-deviations.md`; the approved plans and review artifacts remain untouched.


## Human-directed recursive listing guide and demo

The human requested a concrete guide example and demo for recursive file listing during the execution review. This
extends implementation-plan Task 04 from the API reference to the existing feature guide and runnable demo; approved
plans and review artifacts remain unchanged.

- Expanded `docs/source/features/files.md` with a runnable nested-store Typer example, immediate basename versus
  recursive root-relative keys, loading by returned keys, `missing_ok`, symlink omission, and error behavior.
- Added auto-discovered `demo_6__attach_files__recursive_listing` in `src/typerdrive_demo/attach_files.py`. It stores
  nested files, displays both listing modes, loads each returned recursive key, and demonstrates a missing directory. It
  does not create symlinks.
- Added a focused demo-helper test verifying discovery and captured output without prompts.

Verification:

- `uv run pytest tests/unit/test_demo_helpers.py --no-cov`: 3 passed.
- `make qa`: passed; 441 tests, 93.41% coverage, Ruff, typos, and type checks passed. The run emitted 62
  ResourceWarnings.
- `make docs/build`: succeeded. MkDocs reported two existing broken links in `config.md` and one missing anchor in
  `features/client.md`.

An initial `make qa` run found type errors in the new test's use of the demo-discovery helper's broad callable type. The
test now imports the typed demo function and separately asserts that discovery returns it; the final QA run passed.


## Review iteration 06: Resolve guide invocation and isolation findings

The human requested resolving S01 and S02 from `execution-review--feature--06.md` without editing the review or approved
plans.

- Changed the guide command to `python my_app.py`, matching the single-command Typer app's no-argument invocation.
- Wrapped execution in `tempfile.TemporaryDirectory`, set the files store to that temporary state directory, and
  restored the prior config in `finally`. Each run is isolated and removes its generated files on exit.
- Added `test_files_guide_listing_example_runs_without_arguments`, which extracts the actual guide code, runs it in a
  subprocess with no command arguments, checks expected listing and load output, and asserts the ambient XDG state path
  remains absent.

Verification:

- `uv run pytest tests/unit/test_demo_helpers.py --no-cov`: 4 passed.
- `make qa/lint qa/types`: passed; lint and type checks both reported all checks passed.
- `make docs/build`: succeeded. MkDocs reported two existing broken links in `config.md` and one missing anchor in
  `features/client.md`.

The guide command was verified noninteractively, and the isolated example does not read or write the ambient files
store. No approved plan or review artifact was changed; no commit was made.


## Human correction: move the example into examples

The human requested placing the runnable example in the repository's existing `examples/` tree. Existing feature guides
include those source files with `--8<--` and document commands from the repository root.

- Added `examples/files/listing.py` with the temporary `state_home` configuration retained from the safe inline example.
- Replaced the duplicated guide code block with a snippet include of that file and documented `python
  examples/files/listing.py`.
- Updated `test_files_listing_example_runs_without_arguments` to execute the actual example file from the repository
  root, with no command arguments, while checking output and that ambient XDG state remains untouched. It no longer
  extracts source from Markdown.

Verification:

- `uv run pytest tests/unit/test_demo_helpers.py --no-cov`: 4 passed.
- `make qa`: passed; 442 tests, 93.41% coverage, Ruff, typos, and type checks passed. The run emitted 59
  ResourceWarnings.
- `make docs/build`: succeeded. MkDocs reported two existing broken links in `config.md` and one missing anchor in
  `features/client.md`.

The earlier inline example and its test were superseded. The auto-discovered demo remains unchanged. Approved plans and
review artifacts remain untouched; no commit was made.


## Human correction: immediate item loading in the demo

The human reported that the recursive-listing demo failed while loading the immediate `reports/index.txt` item and
objected to tests that execute demo implementations. The human is removing the demo implementation tests from
`tests/unit/test_demo_helpers.py`; no test file changes were made as part of this journal-only update.

Five serial runs of `uv run pytest tests/unit/test_demo_helpers.py::test_attach_files_recursive_listing_demo --no-cov`
each failed with `FilesLoadError`, printing only `Immediate items:` before the error. This was deterministic, not
shared-config or concurrent-state interference: nonrecursive `list_items("reports")` returns basename `index.txt`, which
is not a storage-root-relative key and cannot be passed directly to `load_text`.

The human's concurrent source correction prefixes `reports/` when loading an immediate basename; recursive listing keys
remain storage-root-relative and load directly. The human reported manually verifying the actual demo with isolated
`XDG_STATE_HOME`, including successful loading of `reports/index.txt` and all recursive items, and reported that `make
qa/lint qa/types` passed. The source and test files were not inspected or edited during this journal-only update.


## Human instruction: keep symlink display coverage in test_dirs

The human instructed: `leave test_dirs, make it ONLY test dirs.py`. The human's concurrent test change replaces the
`LoggingManager.audit` test with a direct `show_directory` symlink-display test and removes the `LoggingManager` import.

The earlier plan called for a logging-audit assertion. This user-directed testing choice supersedes that test scope with
direct coverage of the directory display utility; approved plans and review artifacts were not edited.

The human reported `uv run pytest tests/unit/test_dirs.py --no-cov` passed with 7 tests and `make qa/lint qa/types`
passed. This update records those changes and results in the journals only; no code or test files were touched here.


## Human-requested demo docstring style alignment

The human requested rewriting the `demo_6__attach_files__recursive_listing` docstring in
`src/typerdrive_demo/attach_files.py` to match the neighboring demo function docstrings. The human reported `make
qa/lint qa/types` passed. This is a documentation-style-only change with no intended runtime behavior change; this
update records it in the journals only.

