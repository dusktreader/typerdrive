"""
Provide a class for managing the `typerdrive` files feature.
"""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from typerdrive.files.exceptions import (
    FilesClearError,
    FilesError,
    FilesInitError,
    FilesLoadError,
    FilesStoreError,
)
from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.dirs import is_child


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
        full_path = full_path.resolve()
        FilesError.require_condition(
            is_child(full_path, self.files_dir),
            f"Resolved file path {str(full_path)} is not within files directory {str(self.files_dir)}",
        )
        FilesError.require_condition(
            full_path != self.files_dir,
            f"Resolved file path {str(full_path)} must not be the same as files directory {str(self.files_dir)}",
        )
        if mkdir:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def list_items(self, path: Path | str) -> list[str]:
        """
        List files at a given path.

        Items will be all non-directory entries in the given path.

        If the path doesn't exist or is not a directory, an exception will be raised.
        """
        full_path = self.resolve_path(path)
        FilesError.require_condition(
            full_path.exists(),
            f"Resolved file path {str(full_path)} does not exist",
        )
        FilesError.require_condition(
            full_path.is_dir(),
            f"Resolved file path {str(full_path)} is not a directory",
        )
        items: list[str] = []
        for path in full_path.iterdir():
            if path.is_dir():
                continue
            items.append(str(path.name))
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
