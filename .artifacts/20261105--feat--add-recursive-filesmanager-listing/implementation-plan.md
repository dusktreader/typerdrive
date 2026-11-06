# Implementation Plan: Recursive FilesManager Listing

Add recursive discovery and explicit missing-directory handling to `FilesManager.list_items`, then enforce the approved
symlink policy for file-key operations and the FilesManager directory display. Preserve the existing default listing
shape, logging display behavior, and symlinked configured storage-root support.


## Goal

Implement the approved design in `src/typerdrive/files/manager.py` and the shared directory-display path. Keep default
listing immediate-child-only and basename-shaped. When recursion is requested, return storage-root-relative keys usable
with existing manager operations. Reject root listing, allow missing directories only with `missing_ok=True`, and reject
file keys that cross symlinks below the configured store while omitting symlink entries from listing and FilesManager
display.

Use unit tests for manager and directory behavior, integration coverage for `files show`, and API documentation for the
new options and compatibility rules. Do not add a root-listing API or command. The source design is
`.artifacts/20261105--feat--add-recursive-filesmanager-listing/design-plan.md`, approved with final blocker check PASS
in `design-review--04.md`.


## Project Commands

### Run focused manager and directory tests

Command:

```shell
uv run pytest tests/unit/files/test_manager.py tests/unit/test_dirs.py --no-cov
```

Expected Output:

All selected unit tests pass, including the new path-validation, listing, symlink, and display cases.


### Run focused FilesManager CLI integration tests

Command:

```shell
uv run pytest tests/integration/steps/test_files.py --no-cov
```

Expected Output:

All FilesManager CLI scenarios pass. `files show` output omits symlinks without changing its existing display for
ordinary files and directories.


### Run the complete quality gate

Command:

```shell
make qa
```

Expected Output:

Unit and integration tests, Ruff lint, typos, and `ty` checks all pass. Coverage meets the threshold in
`pyproject.toml`.


### Build the documentation

Command:

```shell
make docs/build
```

Expected Output:

MkDocs builds the project documentation successfully, including the generated FilesManager API reference.


### Format changed Python files

Command:

```shell
uv run ruff check --select I --fix src/typerdrive/files/manager.py src/typerdrive/files/attach.py src/typerdrive/dirs.py tests/unit/files/test_manager.py tests/unit/test_dirs.py tests/integration/steps/test_files.py
uv run ruff format src/typerdrive/files/manager.py src/typerdrive/files/attach.py src/typerdrive/dirs.py tests/unit/files/test_manager.py tests/unit/test_dirs.py tests/integration/steps/test_files.py
```

Expected Output:

Ruff completes without errors and formats only the Python files in this feature's scope.


### Format the Files API documentation

Command:

```shell
dt format markdown docs/source/reference/files.md
```

Expected Output:

The documentation formatter completes successfully and leaves the page formatted according to project Markdown
standards.


## Project Standards

- `pyproject.toml` defines supported Python, test coverage, lint, and type-check settings.
- `Makefile` defines test, quality, and documentation build commands.
- `CONTRIBUTING.md` defines project contribution, documentation, and Python conventions.
- `~/.agents/instructions/python.md` defines Python and docstring conventions.
- `~/.agents/instructions/markdown.md` defines Markdown formatting requirements.
- `.artifacts/20261105--feat--add-recursive-filesmanager-listing/design-plan.md` is the immutable approved behavior
  source.


## Relevant skills and procedures

- `~/.agents/procedures/create-implementation-plan.md`
- `~/.agents/procedures/execute-implementation-plan.md`
- `~/.agents/procedures/review-implementation-execution.md`
- `~/.agents/procedures/qa-implementation.md`


## Execution

### 01: Reject symlinks in explicitly addressed file keys

Centralize the symlink check in the shared path-resolution path so every file-key operation rejects symlink components
below the configured store. Test the behavior first, including the exception for a configured root that resolves through
a symlink.


#### Acceptance Criteria

- AC01: `resolve_path` raises `FilesError` for keys containing a symlink component below `files_dir`, including links to
  internal targets, external targets, and missing targets.
- AC02: `store_bytes`, `load_bytes`, `delete`, and `list_items` reject explicitly addressed symlink paths with
  `FilesError`; rejected writes and deletes do not modify their link targets.
- AC03: A symlinked configured `files_dir` remains usable for normal, symlink-free keys, and those resolved paths remain
  inside the configured store target.
- AC04: Existing symlink-free byte, text, and JSON storage/load tests pass. Deleting a symlink-free key still returns
  its resolved absolute path, leaves sibling files unchanged, and removes empty parent directories as before.


#### Steps

- Add unit tests in `tests/unit/files/test_manager.py` for symlinked file and directory components, internal and
  external targets, broken links, and all affected file-key operations.
- Add a unit test that configures `files_dir` as a symlink to a real directory, then resolves and uses a normal key
  there.
- Run `uv run pytest tests/unit/files/test_manager.py --no-cov` and confirm the new rejection tests fail against the
  current resolver.
- Update `FilesManager.resolve_path` to distinguish the configured root from path components below it, reject symlink
  components in the file key, and retain containment and root-equality checks.
- Run `uv run pytest tests/unit/files/test_manager.py --no-cov` and confirm the new cases and existing manager tests
  pass.


#### Technical Notes

The configured `files_dir` is the trust boundary: symlinks used to reach that configured root are allowed, while
symlinks introduced below it by a file key are rejected. Preserve the current public `resolve_path` return type and
resolved-path semantics for valid keys.


### 02: Add recursive and missing-tolerant listing

Extend `FilesManager.list_items` with explicit `recursive` and `missing_ok` options. Keep the existing default output as
immediate basenames and return root-relative keys only when recursion is enabled.


#### Acceptance Criteria

- AC01: Calling `list_items(path)` remains nonrecursive and returns immediate non-directory entry names in the existing
  `list[str]` shape; it does not include nested files.
- AC02: Calling `list_items(path, recursive=True)` returns keys relative to `files_dir` for files at the requested
  directory and every nested depth. Each result can be passed to existing file operations.
- AC03: `missing_ok` defaults to `False`; missing requested directories raise `FilesError` unless it is `True`, in which
  case the result is `[]`. Combining `recursive=True` and `missing_ok=True` also returns `[]` for a missing directory.
- AC04: Existing paths that are not directories raise `FilesError` with either value of `missing_ok`.
- AC05: An unreadable requested or nested directory raises `FilesError`, retains the filesystem exception as its cause,
  and does not return partial results. `missing_ok=True` does not suppress read errors.
- AC06: Listing omits symlink entries and never traverses symlinked directories in both modes.
- AC07: Listing the configured root raises `FilesError` for `.`, equivalent paths such as `subdirectory/..`, and direct
  configured or resolved root paths, with either listing option combination. No root-level listing API or CLI command is
  added.
- AC08: The listing order remains unspecified.


#### Steps

- Add unit tests in `tests/unit/files/test_manager.py` for immediate-only default results, recursive results rooted at
  `files_dir`, use of returned keys, missing and non-directory paths, and both options together.
- Add tests for root aliases, requested-directory read failures, nested read failures, retained exception causes, no
  partial results, and symlinked files and directories.
- Run `uv run pytest tests/unit/files/test_manager.py --no-cov` and confirm the new behavior tests fail against the
  existing one-argument listing implementation.
- Add `recursive: bool = False` and `missing_ok: bool = False` to `list_items`, preserving the existing default result
  shape and validating the requested path before traversal.
- Implement recursive discovery without following symlinks, generate results relative to `files_dir`, and translate
  requested or nested directory read failures to `FilesError` while retaining the cause.
- Run `uv run pytest tests/unit/files/test_manager.py --no-cov` and confirm all listing and existing manager tests pass.


#### Technical Notes

A recursive call on a nested directory still returns keys relative to the configured storage root, not relative to the
requested directory. Do not add an ordering guarantee. `missing_ok=True` applies only when the requested directory is
absent; it does not mask symlink rejection, non-directory paths, or read failures.


### 03: Filter symlinks only in the FilesManager directory display

Make symlink filtering selectable in the shared directory renderer. Enable it for the FilesManager display while keeping
the logging display's existing default behavior.


#### Acceptance Criteria

- AC01: In a symlink-free `files show` fixture containing `root.txt` with `Stay` and `quotes/yoda.txt` with `Do or do
  not`, plain output contains the `Current files` title, the configured files-root label, both ordinary file names and
  the `quotes` directory, and the footer `Storing 16 Bytes in 2 files`.
- AC02: In a second fixture with the same ordinary files plus a symlink file and a symlink directory to external
  targets, `files show` retains the title, root label, ordinary entries, and `Storing 16 Bytes in 2 files`; it omits
  both symlink names and the target-only nested file.
- AC03: Calling `LoggingManager.audit` on a directory containing `root.txt` with `Stay`, a symlink file to `root.txt`,
  and a symlink directory to an external directory containing `nested.txt` with `hidden`, displays both symlink names
  and `nested.txt`, and reports `Storing 14 Bytes in 3 files`.


#### Steps

- Extend `tests/integration/features/files.feature` and `tests/integration/steps/test_files.py` with separate
  symlink-free and symlink-containing `files show` cases. Assert the exact title, configured root label, ordinary file
  and directory entries, expected file count and byte total, and absence of the symlink names and external target-only
  nested file.
- Add a unit test in `tests/unit/test_dirs.py` that calls `LoggingManager.audit` against a fixture directory with a
  symlink file and a symlink directory pointing outside that directory. Capture output and assert both links and the
  linked directory's child are displayed, with the expected three-file, 14-byte total.
- Run `uv run pytest tests/unit/test_dirs.py tests/integration/steps/test_files.py --no-cov` and confirm the new
  compatibility assertions fail before the implementation change.
- Add an explicit symlink-filter option to the shared directory rendering/display path, preserving the existing default
  rendering behavior.
- Enable filtering only from the FilesManager display caller in `src/typerdrive/files/attach.py`; keep
  `LoggingManager.audit` in `src/typerdrive/logging/manager.py` on the default rendering path.
- Run `uv run pytest tests/unit/test_dirs.py tests/integration/steps/test_files.py --no-cov` and confirm the
  FilesManager filtering and logging compatibility assertions pass.


### 04: Document listing and symlink behavior

Document the new listing parameters and behavioral boundaries in the public FilesManager API documentation.


#### Acceptance Criteria

- AC01: `FilesManager.list_items` documentation states that nonrecursive listing remains the default and returns
  immediate names, while recursive listing returns storage-root-relative keys.
- AC02: Documentation explains explicit `missing_ok` behavior, errors for non-directories/read failures, symlink
  handling, and the prohibition on listing the configured storage root.
- AC03: The generated Files API reference builds successfully and documents the public call signature.


#### Steps

- Update the `list_items` docstring in `src/typerdrive/files/manager.py` with the options, return-key behavior, and
  errors established by Tasks 01 and 02.
- Update `docs/source/reference/files.md` with a concise FilesManager listing example and the root/symlink boundaries.
- Run `dt format markdown docs/source/reference/files.md` and format changed Python files with the scoped Ruff commands
  above.
- Run `make docs/build` and confirm the generated API reference includes the new signature and documentation.


## Unknowns

None. The approved design and caller instructions resolve the listing defaults, missing-path behavior, root restriction,
symlink policy, caller-scoped display, and compatibility requirements.


## Technical Notes

- `FilesManager` and its unit tests are in `src/typerdrive/files/manager.py` and `tests/unit/files/test_manager.py`.
- The current `resolve_path` resolves paths before checking containment, so the shared resolver is the central place to
  enforce explicit-key symlink rejection without changing each operation's public behavior independently.
- `render_directory` is shared by the FilesManager display and logging directory audit. The FilesManager caller is
  `attach_files(show=True)` in `src/typerdrive/files/attach.py`; `LoggingManager.audit` in
  `src/typerdrive/logging/manager.py` must retain the current default.
- `files show` is covered by `tests/integration/steps/test_files.py` and `tests/integration/features/files.feature`. Its
  display is not a request to add a root-listing operation to `FilesManager.list_items`.
- The implementation does not claim race-proof protection against concurrent filesystem changes; that guarantee is
  explicitly outside the approved design.
