import json
from pathlib import Path
from typing import Any

from loguru import logger

from typerdrive.cache.exceptions import (
    CacheClearError,
    CacheError,
    CacheInitError,
    CacheLoadError,
    CacheStoreError,
)
from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.dirs import clear_directory, is_child


# TODO: add a mechanism to cleanup empty directories
# TODO: add more logging and add tests for logging
# TODO: maybe add a test for using root paths (/jawa/ewok) for cache keys?
class CacheManager:
    cache_dir: Path

    def __init__(self):
        config: TyperdriveConfig = get_typerdrive_config()

        self.cache_dir = config.cache_dir

        with CacheInitError.handle_errors("Failed to initialize cache"):
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: Path | str, mkdir: bool = False) -> Path:
        if isinstance(path, str):
            path = Path(path)
        full_path = self.cache_dir / path
        full_path = full_path.resolve()
        CacheError.require_condition(
            is_child(full_path, self.cache_dir),
            f"Resolved cache path {str(full_path)} is not within cache {str(self.cache_dir)}",
        )
        CacheError.require_condition(
            full_path != self.cache_dir,
            f"Resolved cache path {str(full_path)} must not be the same as cache {str(self.cache_dir)}",
        )
        if mkdir:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def store_bytes(self, data: bytes, path: Path | str, mode: int | None = None):
        full_path = self.resolve_path(path, mkdir=True)

        logger.debug(f"Storing data at {full_path}")

        with CacheStoreError.handle_errors(f"Failed to store data in cache target {str(path)}"):
            full_path.write_bytes(data)
        if mode:
            with CacheStoreError.handle_errors(f"Failed to set mode for cache target {str(path)} to {mode=}"):
                full_path.chmod(mode)

    def store_text(self, text: str, path: Path | str, mode: int | None = None):
        self.store_bytes(text.encode("utf-8"), path, mode=mode)

    def store_json(self, data: dict[str, Any], path: Path | str, mode: int | None = None):
        self.store_bytes(json.dumps(data, indent=2).encode("utf-8"), path, mode=mode)

    def load_bytes(self, path: Path | str) -> bytes:
        full_path = self.resolve_path(path, mkdir=False)

        logger.debug(f"Loading data from {full_path}")

        CacheLoadError.require_condition(full_path.exists(), f"Cache target {str(path)} does not exist")
        with CacheLoadError.handle_errors(f"Failed to load data from cache target {str(path)}"):
            return full_path.read_bytes()

    def load_text(self, path: Path | str) -> str:
        return self.load_bytes(path).decode("utf-8")

    def load_json(self, path: Path | str) -> dict[str, Any]:
        text = self.load_bytes(path).decode("utf-8")
        with CacheLoadError.handle_errors(f"Failed to unpack JSON data from cache target {str(path)}"):
            return json.loads(text)

    def clear_path(self, path: Path | str) -> Path:
        full_path = self.resolve_path(path)

        logger.debug(f"Clearing data at {full_path}")

        with CacheClearError.handle_errors(f"Failed to clear cache target {str(path)}"):
            full_path.unlink()
        if len([p for p in full_path.parent.iterdir()]) == 0:
            with CacheClearError.handle_errors(f"Failed to remove empty directory {str(full_path.parent)}"):
                full_path.parent.rmdir()
        return full_path

    def clear_all(self) -> int:
        logger.debug("Clearing entire cache")
        with CacheClearError.handle_errors("Failed to clear cache"):
            return clear_directory(self.cache_dir)
