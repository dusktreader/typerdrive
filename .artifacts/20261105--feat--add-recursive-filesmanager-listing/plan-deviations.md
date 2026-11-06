# Post-plan changes: Recursive FilesManager listing

A chronological record of implementation changes made against the approved design and implementation plans.


## Source plans

- Design plan: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/design-plan.md`
- Implementation plan: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/implementation-plan.md`


## Changes

### Change 01: Reject symlinks in explicitly addressed file keys

#### Stage and source

Implementation, requested by the approved implementation plan, Task 01. The behavior follows design-plan AC06 through
AC08.


#### Request

Centralize symlink rejection for file-key operations below the configured store while allowing a symlinked configured
root.


#### Plan alignment

Follows Task 01 and its AC01 through AC04. No behavior outside the approved symlink policy was added.


#### Change made

`FilesManager.resolve_path` now checks path components before resolution, then enforces the resolved containment and
root-equality restrictions.

- UPDATED: `src/typerdrive/files/manager.py`
- UPDATED: `tests/unit/files/test_manager.py`


#### Reason

The approved implementation plan requires consistent rejection through the shared resolver and protection against writes
or deletes modifying link targets.


#### Verification

The new resolver and manager-operation tests failed against the original implementation and passed after the change. `uv
run pytest tests/unit/files/test_manager.py --no-cov` passed.


### Change 02: Add recursive and missing-tolerant listing

#### Stage and source

Implementation, requested by the approved implementation plan, Task 02. The behavior follows design-plan AC01 through
AC07.


#### Request

Add explicit recursive discovery and optional empty results for missing requested directories while preserving default
listing behavior.


#### Plan alignment

Follows Task 02 and its AC01 through AC08. The implementation adds no ordering guarantee or root-listing API.


#### Change made

`list_items` now supports `recursive` and `missing_ok`, returns root-relative recursive keys, omits symlinks, and
translates directory-read errors to `FilesError` with their causes retained.

- UPDATED: `src/typerdrive/files/manager.py`
- UPDATED: `tests/unit/files/test_manager.py`


#### Reason

The approved implementation plan requires recursive key discovery, explicit missing behavior, full-request failures, and
symlink omission.


#### Verification

New listing tests failed against the original one-argument method. The manager unit suite passed after implementation
and again in final verification.


### Change 03: Filter symlinks only in the FilesManager display

#### Stage and source

Implementation, requested by the approved implementation plan, Task 03. The behavior follows design-plan AC09.


#### Request

Omit symlink entries and linked contents from the FilesManager display without changing logging display behavior.


#### Plan alignment

The display behavior and caller scope follow Task 03 and AC01 through AC03. The renderer and FilesManager caller changes
were made before adding the new display assertions, so execution deviated from the plan's test-first step order. The new
assertions subsequently passed; the behavior and task scope did not change.


#### Change made

The shared renderer has an opt-in symlink filter. `attach_files(show=True)` enables filtering; logging retains the
default. Separate CLI scenarios and a logging audit test verify the output and counts.

- UPDATED: `src/typerdrive/dirs.py`
- UPDATED: `src/typerdrive/files/attach.py`
- UPDATED: `tests/unit/test_dirs.py`
- UPDATED: `tests/integration/features/files.feature`
- UPDATED: `tests/integration/steps/test_files.py`


#### Reason

The implementation plan requires caller-scoped filtering and explicitly preserves logging behavior. No separate reason
was provided for the test-first sequencing departure.


#### Verification

`uv run pytest tests/unit/test_dirs.py tests/integration/steps/test_files.py --no-cov` passed after adding the
assertions. The focused unit and integration suites passed again during final verification.


### Change 04: Document listing and symlink behavior

#### Stage and source

Implementation, requested by the approved implementation plan, Task 04. The behavior follows design-plan compatibility
and listing criteria.


#### Request

Document the new listing parameters and behavioral boundaries in the public FilesManager API reference.


#### Plan alignment

Follows Task 04 and its AC01 through AC03. No undocumented API or behavior was introduced.


#### Change made

The method docstring and Files API page document options, result shapes, errors, symlink policy, and the root-listing
restriction. The reference page includes a listing example.

- UPDATED: `src/typerdrive/files/manager.py`
- UPDATED: `docs/source/reference/files.md`


#### Reason

The approved implementation plan requires public API documentation for the new options and compatibility rules.


#### Verification

`dt format markdown docs/source/reference/files.md` completed. `make docs/build` succeeded and generated the API
reference with the updated signature and docstring. `make qa` passed with 432 tests, Ruff, typos, and `ty` checks. The
test run emitted 62 ResourceWarnings; MkDocs reported three existing broken-link or missing-anchor warnings.


### Change 05: Add coverage for execution review findings

#### Stage and source

Code review, requested by findings C01 and S01 in
`.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-review--feature--01.md` and by the user.


#### Request

Assert empty-parent cleanup, ensure `missing_ok=True` does not conceal broken or intermediate symlinks, and reject
configured-root aliases when the configured storage root is a symlink.


#### Plan alignment

Follows Task 01 AC04 and Task 02 AC03/AC07, plus design-plan AC05 and AC07. It adds regression coverage without changing
approved behavior or modifying production code.


#### Change made

Added focused manager tests for deletion cleanup, missing-tolerant symlink rejection, and root aliases through a
symlinked configured root. Corrected the execution journal's AC04 evidence to point to a dedicated cleanup test.

- UPDATED: `tests/unit/files/test_manager.py`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-journal.md`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/plan-deviations.md`


#### Reason

The reviewer identified these behaviors as lacking regression coverage. The tests pass against the current
implementation, so no production defect or source change was needed.


#### Verification

`uv run pytest tests/unit/files/test_manager.py tests/unit/test_dirs.py --no-cov` passed with 58 tests. Ruff import
checks and formatting passed for `tests/unit/files/test_manager.py`.


### Change 06: Make symlink display and directory clearing uniformly safe

#### Stage and source

Implementation, requested by the human after approval in the current execution-review discussion.


#### Request

Remove `exclude_symlinks` from the shared directory APIs and omit symlink entries from all displays, including logging.
Make directory clearing unlink symlink entries instead of following them, including directory, dangling, nested, and
cyclic links.


#### Plan alignment

This intentionally departs from design-plan AC09 and implementation-plan Task 03 AC03, which require logging to retain
symlink-following display behavior. The human agreed that the logging feature need not follow links. The
`clear_directory` change extends beyond the approved plans; it does not change FilesManager's approved configured-root
symlink support.


#### Change made

`render_directory` and `show_directory` now omit symlinks unconditionally. `attach_files` no longer passes a filter
option. The initial `clear_directory` implementation unlinked nested symlink entries and rejected a symlink root. The
root rejection was later superseded by Change 07. Its docstring describes the final behavior.

- UPDATED: `src/typerdrive/dirs.py`
- UPDATED: `src/typerdrive/files/attach.py`
- UPDATED: `tests/unit/test_dirs.py`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-journal.md`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/plan-deviations.md`


#### Reason

The human requested this change because the logging feature need not follow links and directory clearing should not
follow symlink targets or alter them.


#### Verification

The new focused tests initially failed against the previous behavior, including target cleanup through directory
symlinks, cycle traversal, and logging link display. Then `uv run pytest tests/unit/test_dirs.py
tests/unit/files/test_manager.py --no-cov tests/integration/steps/test_files.py --no-cov` passed with 69 tests. `make
qa` passed with 440 tests, 93.41% coverage, Ruff, typos, and `ty` checks. `make docs/build` succeeded. That QA run
emitted 62 ResourceWarnings; MkDocs reported three broken-link or missing-anchor warnings in unchanged pages.


### Change 07: Preserve clearing through a symlinked root

#### Stage and source

Human-directed correction to Change 06.


#### Request

Keep the previous behavior when the explicitly supplied `clear_directory` root is a symlink: clear the directory it
designates. Continue unlinking nested symlink entries without traversing or modifying their targets.


#### Plan alignment

This correction restores prior root-path behavior and does not change FilesManager's configured-root symlink policy. It
supersedes Change 06's unsupported symlink-root rejection.


#### Change made

Removed the root symlink rejection and documented that the target directory path may itself be a symlink. Replaced the
root-rejection test with `test_clear_directory__follows_symlinked_root_without_following_nested_links`, which verifies
the target directory is cleared while the nested symlink target remains unchanged.

- UPDATED: `src/typerdrive/dirs.py`
- UPDATED: `tests/unit/test_dirs.py`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-journal.md`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/plan-deviations.md`


#### Reason

The human clarified that the symlink-safety requirement applies to entries inside the directory, not to the explicitly
provided root path. The root must retain its prior target-designating behavior.


#### Verification

The focused unit and Files CLI tests passed with 69 tests. Latest `make qa` passed with 440 tests, 93.41% coverage,
Ruff, typos, and `ty`; it emitted 57 ResourceWarnings. `make docs/build` succeeded with two broken-link warnings and one
missing-anchor warning in unchanged pages.


### Change 08: Investigate the unrelated settings test failure

#### Stage and source

Investigation requested from finding C01 in `execution-review--feature--03.md`.


#### Request

Determine whether the reported `hutt` versus `jawa` failure in `tests/unit/test_handle_errors.py:55` is a feature
regression or an unrelated flaky/environment-dependent test. Run a focused reproduction and full `make qa`, document
results, and avoid unrelated fixes.


#### Finding

The failure is unrelated to the FilesManager changes. The test defines a model default of `jawa`, then attaches
settings. `SettingsManager.__init__` loads JSON from `config.settings_path` when that file exists before constructing
the model (`src/typerdrive/settings/manager.py:46-57`). The root `tests/conftest.py` sets `app_name="test"` without
isolating `state_home` (`tests/conftest.py:9-14`). Its temporary settings-path fixture is scoped to
`tests/unit/settings/`, so it does not cover this test (`tests/unit/settings/conftest.py:9-23`). An ambient XDG settings
file containing `name: "hutt"` therefore overrides the default and produces the review's exact mismatch. This is
environment-sensitive test isolation, not a feature regression; the old failure was not reproduced in this worktree.


#### Change made

No source or test fix was made. Recorded the failure mechanism and verification in this journal and the execution
journal. The approved plans and review artifacts were not edited.

- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-journal.md`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/plan-deviations.md`


#### Verification

- `uv run pytest
  tests/unit/test_handle_errors.py::TestHandleErrors::test_handle_errors__no_conflict_with_attach_settings --no-cov`: 1
  passed.
- `make qa`: passed; 440 tests, 93.41% coverage, Ruff, typos, and type checks passed. The run emitted 61
  ResourceWarnings.

The full quality gate is green in the current environment. No unrelated settings test changes were made.


### Change 09: Document shared symlink behavior

#### Stage and source

Post-plan documentation fix for finding S01 in `execution-review--feature--04.md`.


#### Request

Clarify that shared directory displays and logging audits omit symlink entries without traversing targets. Explain that
clearing through a symlinked root clears the designated directory, preserves the root link, and unlinks nested symlinks
without modifying their targets.


#### Plan alignment

This documentation records the human-directed behavior from Changes 06 and 07 without changing runtime behavior.


#### Change made

Expanded the `clear_directory`, `render_directory`, and `show_directory` docstrings and the logging audit docstring.

- UPDATED: `src/typerdrive/dirs.py`
- UPDATED: `src/typerdrive/logging/manager.py`


#### Reason

Finding S01 identified that the generated public API references omitted these display and clearing semantics.


#### Verification

`make qa` passed with 440 tests, 93.41% coverage, Ruff, typos, and `ty` checks. It emitted 59 ResourceWarnings. `make
docs/build` succeeded, and the generated base-module and logging references include the new behavior details. MkDocs
reported the existing broken-link and missing-anchor warnings in `config.md` and `features/client.md`.


### Change 10: Add a recursive listing guide example and demo

#### Stage and source

Post-plan addition requested by the human during execution review.


#### Request

Extend the existing Files feature guide with a runnable nested-store example contrasting default basenames and recursive
storage-root-relative keys, showing use of returned keys with `load`, documenting `missing_ok`, symlink behavior, and
errors. Add an auto-discovered demo for nested storage, both listing modes, loading by recursive keys, and `missing_ok`,
plus a focused test. Do not add a symlink-creation facility.


#### Plan alignment

This extends implementation-plan Task 04's API documentation to the existing feature guide and demo module. The human
explicitly requested this post-plan scope. No approved plan or review artifact was changed, and the feature API and
symlink behavior were not modified.


#### Change made

Added the listing example and behavior details to `docs/source/features/files.md`. Added
`demo_6__attach_files__recursive_listing` to `src/typerdrive_demo/attach_files.py`; the demo helper discovers it by its
name, and a test checks discovery and runs it through the noninteractive capture helper.

- UPDATED: `docs/source/features/files.md`
- UPDATED: `src/typerdrive_demo/attach_files.py`
- UPDATED: `tests/unit/test_demo_helpers.py`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-journal.md`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/plan-deviations.md`


#### Verification

`uv run pytest tests/unit/test_demo_helpers.py --no-cov` passed with 3 tests. Final `make qa` passed with 441 tests,
93.41% coverage, Ruff, typos, and type checks; it emitted 62 ResourceWarnings. `make docs/build` succeeded. MkDocs
reported two existing broken links in `config.md` and one missing anchor in `features/client.md`. Both Markdown files
were formatted with `dt format markdown`.


### Change 11: Fix guide invocation and isolate its files store

#### Stage and source

Human-directed resolution of findings S01 and S02 in `execution-review--feature--06.md`.


#### Request

Make the documented command for the single-command Typer example runnable, and prevent it from overwriting or being
affected by persistent application files. Verify the exact guide code noninteractively, run focused demo tests, relevant
lint/type checks, and the documentation build.


#### Plan alignment

This corrects the post-plan guide addition from Change 10 and addresses the review findings without changing the Files
API or demo behavior. The human requested this scope. Approved plans and review artifacts remain unchanged.


#### Change made

Changed the guide command to `python my_app.py`, which invokes the app's single command without a subcommand argument.
The example now sets `state_home` to a `TemporaryDirectory` for the duration of the command and restores the prior
config in `finally`. Added a test that extracts the actual Python block from the guide, launches it without arguments,
checks its output, and verifies the ambient XDG state directory remains absent.

- UPDATED: `docs/source/features/files.md`
- UPDATED: `tests/unit/test_demo_helpers.py`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-journal.md`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/plan-deviations.md`


#### Verification

`uv run pytest tests/unit/test_demo_helpers.py --no-cov` passed with 4 tests. `make qa/lint qa/types` passed both
checks. `make docs/build` succeeded; MkDocs reported two existing broken links in `config.md` and one missing anchor in
`features/client.md`. The exact guide code was exercised without arguments in the focused test, and no ambient state was
created.


### Change 12: Move the guide example into examples

#### Stage and source

Human-directed correction to Change 11.


#### Request

Place the runnable recursive-listing example in the existing `examples/` tree. Reference that single source from the
guide without maintaining a duplicated inline implementation, preserve its safe temporary storage, and test the actual
example file noninteractively.


#### Plan alignment

This follows the established example layout and documentation pattern of including `examples/` source files with
`--8<--`. It supersedes Change 11's inline code block and source-extraction test while preserving the temporary
`state_home` safeguard. It adds no feature behavior or symlink creation facility.


#### Change made

Created `examples/files/listing.py`, changed the guide to include that source and run it from the repository root with
`python examples/files/listing.py`, and changed the test to execute the real example file with no arguments and assert
the ambient XDG path remains absent.

- ADDED: `examples/files/listing.py`
- UPDATED: `docs/source/features/files.md`
- UPDATED: `tests/unit/test_demo_helpers.py`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/execution-journal.md`
- UPDATED: `.artifacts/20261105--feat--add-recursive-filesmanager-listing/plan-deviations.md`


#### Verification

`uv run pytest tests/unit/test_demo_helpers.py --no-cov` passed with 4 tests. `make qa` passed with 442 tests, 93.41%
coverage, Ruff, typos, and type checks; it emitted 59 ResourceWarnings. `make docs/build` succeeded. MkDocs reported two
existing broken links in `config.md` and one missing anchor in `features/client.md`. The focused test ran
`examples/files/listing.py` noninteractively from the repository root and confirmed no ambient state directory was
created.


### Change 13: Correct immediate file loading in the recursive-listing demo

#### Stage and source

Human-directed correction after finding C01 in `execution-review--feature--09.md`.


#### Request

Investigate the demo's `FilesLoadError`, preserve the human's concurrent demo edits, remove demo implementation tests
per the human's direction, and record verification without editing test files.


#### Finding and plan alignment

Five serial runs of the focused test each failed with `FilesLoadError` immediately after printing `Immediate items:`.
The failure is deterministic: nonrecursive listing returns basenames, while `load_text` requires a storage-root-relative
key. It is not caused by shared global configuration or concurrent test state. Correcting how the demo loads listed
files does not change the FilesManager API or approved plans.


#### Change made

The human's concurrent update to `src/typerdrive_demo/attach_files.py` prefixes `reports/` when loading a nonrecursive
basename; recursive keys remain directly loadable. The human is removing demo implementation tests from
`tests/unit/test_demo_helpers.py`. This assistant made no changes to the demo or test files and did not inspect the test
file after the human's removal instruction. This update changes only the execution journal and this deviation record.


#### Verification

The human reported manual verification using an isolated `XDG_STATE_HOME`: the reports index and recursive items loaded
successfully. The human also reported `make qa/lint qa/types` passed. The pre-correction focused test was run five times
serially and failed all five times with the same `FilesLoadError` and captured output beginning `Immediate items:`.


### Change 14: Keep symlink display coverage in test_dirs only

#### Stage and source

Human-directed test-scope correction following Change 13.


#### Request

The human instructed: `leave test_dirs, make it ONLY test dirs.py`. Replace the `LoggingManager.audit` test with a
direct `show_directory` symlink-display test, remove the `LoggingManager` import, and leave the test changes to the
human.


#### Plan alignment

The earlier plan expected symlink-display coverage through a logging audit. The user-directed direct directory-utility
test supersedes that testing choice; it does not change the intended display behavior. Approved plans and review
artifacts remain untouched.


#### Change made

The human's concurrent test change replaces the audit test with the direct `show_directory` test and removes the import.
This assistant made no code or test edits and updated only these journals.


#### Verification

The human reported `uv run pytest tests/unit/test_dirs.py --no-cov` passed with 7 tests and `make qa/lint qa/types`
passed. These reported results were recorded without inspecting or changing the concurrent test file.


### Change 15: Align the recursive-listing demo docstring

#### Stage and source

Human-requested style correction to the demo added in Change 10.


#### Request

Rewrite the `demo_6__attach_files__recursive_listing` docstring in `src/typerdrive_demo/attach_files.py` to match the
neighboring demo function docstrings.


#### Plan alignment

This aligns the demo documentation with local conventions and does not change runtime behavior or any approved plan.


#### Change made

The human updated the demo docstring. This assistant updated only the journals and did not edit or inspect the source
file.


#### Verification

The human reported `make qa/lint qa/types` passed.
