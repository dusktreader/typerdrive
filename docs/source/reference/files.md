# typerdrive Files modules

## Listing files

Use `FilesManager.list_items` to list files from directories below the configured files directory:

```python
from typerdrive.files.manager import FilesManager

manager = FilesManager()
manager.list_items("documents")
manager.list_items("documents", recursive=True)
manager.list_items("documents", recursive=True, missing_ok=True)
manager.list_items("documents", recursive=True, pattern="*.md")
manager.list_items("documents", recursive=True, pattern="**/*.md")
```

Listing is nonrecursive by default and returns immediate file names. Recursive listing returns storage-root-relative
keys, including files nested below the requested directory. A single optional glob pattern filters files relative to the
requested directory. Patterns support `*`, `?`, and bracket expressions within path components; `/` separates path
components, and `**` as a path component matches zero or more directories. Thus, `*.md.j2` matches immediate files only,
while `**/*.md.j2` also matches nested files. `recursive=False` remains nonrecursive regardless of the pattern.
Wildcards can match dot-prefixed names. `missing_ok=True` returns an empty list only when the requested directory is
missing. Non-directories, unreadable directories, and explicit paths through symlinks raise `FilesError`. Listings omit
symlink entries and never follow symlinked directories. The configured files root cannot be listed, including through
equivalent paths such as `.` or `subdirectory/..`.

::: typerdrive.files.attach
    options:
      filters:
      - "!(P|T|ContextFunction)"
::: typerdrive.files.commands

::: typerdrive.files.exceptions

::: typerdrive.files.manager
