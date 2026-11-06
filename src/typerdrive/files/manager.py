"""
Provide a class for managing the `typerdrive` files feature.
"""

import json
from fnmatch import fnmatchcase
from functools import cache
from pathlib import Path
from typing import Any

from loguru import logger

from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.dirs import is_child
from typerdrive.files.exceptions import (
    FilesClearError,
    FilesError,
    FilesInitError,
    FilesLoadError,
    FilesStoreError,
)


class FilesManager:
    """
    Manage the `typerdrive` files feature.

    This manager provides a simple key-value file storage system where files are stored
    in a directory structure. Files can be stored as bytes, text, or JSON and retrieved
    the same way.
    """

    files_dir: Path
    """ The directory where files are stored. """

    def __init__(self):
        config: TyperdriveConfig = get_typerdrive_config()

        self.files_dir = config.files_dir

        with FilesInitError.handle_errors("Failed to initialize files storage"):
            self.files_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def matches_glob(path: str, pattern: str) -> bool:
        """
        Checks if a given path matches a supplied glob pattern.

        Note:
            Replace with `glob.translate` once Python 3.12 support is dropped; it is unavailable in Python 3.12.
        """
        path_parts = path.split("/")
        pattern_parts = pattern.split("/")

        @cache
        def matches(path_index: int, pattern_index: int) -> bool:
            if pattern_index == len(pattern_parts):
                return path_index == len(path_parts)
            if pattern_parts[pattern_index] == "**":
                return matches(path_index, pattern_index + 1) or (
                    path_index < len(path_parts) and matches(path_index + 1, pattern_index)
                )
            return (
                path_index < len(path_parts)
                and fnmatchcase(path_parts[path_index], pattern_parts[pattern_index])
                and matches(path_index + 1, pattern_index + 1)
            )

        return matches(0, 0)

    def resolve_path(self, path: Path | str, mkdir: bool = False) -> Path:
        """
        Resolve a given file key path to an absolute path within the files directory.

        If the resolved path is outside the files directory, an exception will be raised.
        If the resolved path is the same as the files directory, an exception will be raised.

        Parameters:
            path:  The file key
            mkdir: If set, create the directory for the file key if it does not exist.
        """
        if isinstance(path, str):
            path = Path(path)
        full_path = self.files_dir / path
        resolved_files_dir = self.files_dir.resolve()
        try:
            relative_path = full_path.relative_to(self.files_dir)
            component_root = self.files_dir
        except ValueError:
            try:
                relative_path = full_path.relative_to(resolved_files_dir)
                component_root = resolved_files_dir
            except ValueError:
                relative_path = None
                component_root = self.files_dir
        if relative_path is not None:
            component_path = component_root
            for part in relative_path.parts:
                if part in ("", "."):
                    continue
                component_path /= part
                FilesError.require_condition(
                    not component_path.is_symlink(),
                    f"File path {str(path)} contains a symlink component at {str(component_path)}",
                )
        full_path = full_path.resolve()
        FilesError.require_condition(
            is_child(full_path, resolved_files_dir),
            f"Resolved file path {str(full_path)} is not within files directory {str(self.files_dir)}",
        )
        FilesError.require_condition(
            full_path != resolved_files_dir,
            f"Resolved file path {str(full_path)} must not be the same as files directory {str(self.files_dir)}",
        )
        if mkdir:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def list_items(
        self,
        path: Path | str,
        recursive: bool = False,
        missing_ok: bool = False,
        pattern: str | None = None,
    ) -> list[str]:
        """
        List files in a directory below the configured files directory.

        Nonrecursive listing returns immediate file names. Recursive listing returns keys relative to the configured files
        directory, including files nested below the requested directory. Symlink entries are omitted and never traversed.
        The configured files directory itself cannot be listed.

        A glob pattern filters files relative to the requested directory. Patterns support `*`, `?`, and bracket
        expressions within path components, with `/` as the path separator. A `**` path component matches zero or more
        directories, so `*.md.j2` matches only immediate files while `**/*.md.j2` also matches nested files. Wildcards
        can match dot-prefixed names. Only one pattern is supported.

        Parameters:
            path: The directory key to list
            recursive: If set, include files from nested directories
            missing_ok: If set, return an empty list when the requested directory is missing
            pattern: If set, include only files matching this glob pattern

        Raises:
            FilesError: If the requested directory is missing and missing_ok is false, is not a directory, is unreadable,
                is the configured root, or contains a symlink component
        """
        full_path = self.resolve_path(path)
        if not full_path.exists():
            if missing_ok:
                return []
            FilesError.require_condition(
                False,
                f"Resolved file path {str(full_path)} does not exist",
            )
        FilesError.require_condition(
            full_path.is_dir(),
            f"Resolved file path {str(full_path)} is not a directory",
        )
        items: list[str] = []

        def collect(directory: Path):
            with FilesError.handle_errors(f"Failed to list directory {str(directory)}"):
                entries = list(directory.iterdir())
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    if recursive:
                        collect(entry)
                else:
                    relative_path = entry.relative_to(full_path).as_posix()
                    if pattern is not None and not self.matches_glob(relative_path, pattern):
                        continue
                    if recursive:
                        items.append(entry.relative_to(self.files_dir.resolve()).as_posix())
                    else:
                        items.append(entry.name)

        collect(full_path)
        return items

    def store_bytes(self, data: bytes, path: Path | str, mode: int | None = None):
        """
        Store binary data as a file at the given key.

        Parameters:
            data: The binary data to store
            path: The file key where the data should be stored
            mode: The file mode to use when creating the file
        """
        full_path = self.resolve_path(path, mkdir=True)

        logger.debug(f"Storing file at {full_path}")

        with FilesStoreError.handle_errors(f"Failed to store file at {str(path)}"):
            full_path.write_bytes(data)
        if mode:
            with FilesStoreError.handle_errors(f"Failed to set mode for file at {str(path)} to {mode=}"):
                full_path.chmod(mode)

    def store_text(self, text: str, path: Path | str, mode: int | None = None):
        """
        Store text as a file at the given key.

        Parameters:
            text: The text to store
            path: The file key where the text should be stored
            mode: The file mode to use when creating the file
        """
        self.store_bytes(text.encode("utf-8"), path, mode=mode)

    def store_json(self, data: dict[str, Any], path: Path | str, mode: int | None = None):
        """
        Store a dictionary as a JSON file at the given key.

        The dictionary must be json serializable.

        Parameters:
            data: The dict to store as JSON
            path: The file key where the JSON should be stored
            mode: The file mode to use when creating the file
        """
        self.store_bytes(json.dumps(data, indent=2).encode("utf-8"), path, mode=mode)

    def load_bytes(self, path: Path | str) -> bytes:
        """
        Load binary data from a file at the given key.

        If there is no file at the given key, an exception will be raised.
        If there is an error reading the file, an exception will be raised.

        Parameters:
            path: The file key where the data should be loaded from
        """
        full_path = self.resolve_path(path, mkdir=False)

        logger.debug(f"Loading file from {full_path}")

        FilesLoadError.require_condition(full_path.exists(), f"File at {str(path)} does not exist")
        with FilesLoadError.handle_errors(f"Failed to load file from {str(path)}"):
            return full_path.read_bytes()

    def load_text(self, path: Path | str) -> str:
        """
        Load text from a file at the given key.

        Parameters:
            path: The file key where the text should be loaded from
        """
        return self.load_bytes(path).decode("utf-8")

    def load_json(self, path: Path | str) -> dict[str, Any]:
        """
        Load a dictionary from a JSON file at the given key.

        The file at the given key must be valid JSON.

        Parameters:
            path: The file key where the JSON should be loaded from
        """
        text = self.load_bytes(path).decode("utf-8")
        with FilesLoadError.handle_errors(f"Failed to parse JSON from file at {str(path)}"):
            return json.loads(text)

    def delete(self, path: Path | str) -> Path:
        """
        Delete a file at the given key.

        Parameters:
            path: The file key where the file should be deleted
        """
        full_path = self.resolve_path(path)

        logger.debug(f"Deleting file at {full_path}")

        with FilesClearError.handle_errors(f"Failed to delete file at {str(path)}"):
            full_path.unlink()

        # Clean up empty parent directories
        if len([p for p in full_path.parent.iterdir()]) == 0:
            with FilesClearError.handle_errors(f"Failed to remove empty directory {str(full_path.parent)}"):
                full_path.parent.rmdir()
        return full_path
