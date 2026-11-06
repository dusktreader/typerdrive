# Design Plan: Recursive FilesManager Listing

Add recursive discovery to `FilesManager` while preserving the existing default listing behavior and establishing a
consistent symlink policy for file storage. Recursive results use storage-root-relative file keys so consumers can pass
discovered keys to the manager's existing file operations.


## Goal

Let applications discover files nested below a chosen directory through the `FilesManager` API instead of walking its
storage directory themselves. Recursion and empty results for missing directories are explicit options; defaults retain
current strict, immediate-child behavior.

Define predictable symlink handling across file storage operations and the FilesManager directory display. This is an
intentional pre-1.0 breaking change: operations no longer access explicitly addressed paths through symlinks inside the
managed store, and listings no longer expose symlink entries.


## Acceptance Criteria

### Listing behavior

#### AC01: Preserve nonrecursive listing by default

Without `recursive=True`, listing returns only the immediate file names and retains the current result shape. The
default remains nonrecursive.


#### AC02: Return usable keys for recursive results

With `recursive=True`, listing a supported directory below the configured storage root includes files at that directory
and at any depth below it. Each result is a relative file key rooted at the configured storage directory and can be
passed to existing file operations.


#### AC03: Make missing-directory handling optional

Without `missing_ok=True`, a missing listing directory continues to raise `FilesError`. With `missing_ok=True`, a
missing directory returns an empty list, including when recursive listing is enabled. An existing path that is not a
directory raises `FilesError` in either mode. The two options can be used together.


#### AC04: Fail listing on directory read errors

If listing cannot read the requested directory or, in recursive mode, any nested directory, it raises `FilesError` with
the filesystem failure retained as its cause. It returns no results. `missing_ok=True` applies only when the requested
directory does not exist; it does not suppress read errors.


#### AC05: Reject listing the configured storage root

Listing raises `FilesError` when the requested path resolves to the configured storage root. This includes `.`,
equivalent paths such as `subdirectory/..`, and direct paths to either the configured root or its resolved target. The
restriction applies to recursive and nonrecursive listing, with or without `missing_ok=True`; the storage root is not a
valid file key.


### Symlink policy

#### AC06: Omit symlinks from listing results

Nonrecursive and recursive listings omit symlink entries and do not traverse symlinked directories.


#### AC07: Reject explicitly addressed symlink paths

File-key operations reject an explicitly addressed path containing a symlink below the managed storage root with
`FilesError`. This applies to reads, writes, deletes, listings, and file-key resolution, including when
`missing_ok=True` is requested.


#### AC08: Allow a symlinked configured storage root

The configured storage root may itself resolve through a symlink. This exception does not permit symlinks within that
root. FilesManager adds no facility for creating symlinks.


### Caller-scoped display

#### AC09: Filter symlinks only in the FilesManager display

The FilesManager directory display, including `files show`, omits symlink entries and does not count or follow them. The
logging directory display retains its existing symlink behavior.


### Compatibility

#### AC10: Preserve storage and load behavior for symlink-free keys

For keys without symlink components, existing byte, text, and JSON storage remains retrievable with the corresponding
load operation.


#### AC11: Preserve deletion behavior for symlink-free keys

For a key without symlink components, deletion removes only the addressed file, leaves sibling files unchanged, returns
the resolved absolute file path, and retains existing empty-parent cleanup behavior.


## Architecture

FilesManager listing operates on the existing local file store and accepts only directories strictly below the
configured storage root. The storage root itself is not listable in either mode, so recursive listing does not provide a
full-store listing or return root-level files. The restriction applies to every path that resolves to the root,
including `.` and equivalent paths, whether the configured root is a normal directory or a symlink. Nonrecursive listing
returns immediate file names; recursive listing discovers files below an accepted directory and returns keys relative to
the configured storage root. The optional missing-directory behavior does not make an existing non-directory path valid.

Directory-read failures in either listing mode raise `FilesError` with the filesystem failure retained as its cause and
produce no results. Recursive discovery also fails as a whole if any nested directory cannot be read. The missing-path
option does not suppress these failures.

All explicit file-key access uses one symlink policy: paths within the managed store that resolve through symlink
components are rejected. Listings omit symlink entries rather than following them. The configured storage root itself is
allowed to be symlinked. This does not claim race-proof protection against concurrent filesystem changes; no such
guarantee is part of this design.

The shared directory-display capability applies symlink handling per caller. The FilesManager display opts to omit
symlink entries; logging retains its existing display behavior. This keeps the changed policy scoped to file storage. No
storage backend abstraction or symlink creation capability is introduced.


## Unknowns

No unresolved design questions remain.


## Technical Notes

- FilesManager currently stores files in a local directory configured for the application; there are no alternate or
  remote storage backends to reconcile.
- Current path validation does not consistently recognize equivalent root paths when the configured root is symlinked.
  The contract distinguishes the permitted symlinked storage location from the prohibited root listing by resolved root
  identity.
- Existing immediate listing returns basenames and does not define ordering. This design adds no ordering guarantee.
- Existing listing raises `FilesError` for a missing path or a path that is not a directory, but currently does not wrap
  filesystem errors encountered while iterating. This design makes listing read failures `FilesError` in both modes,
  retains the filesystem failure as the cause, and limits `missing_ok=True` to missing directories.
- The current `files show` and logging displays share directory-rendering behavior. Symlink filtering must be selected
  by the FilesManager display caller so logging retains its existing behavior.
