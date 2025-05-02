from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import humanize
from rich.markup import escape
from rich.text import Text
from rich.tree import Tree

from typerdrive.cache.exceptions import (
    CacheClearError,
    CacheError,
    CacheInitError,
    CacheLoadError,
    CacheStoreError,
)


def get_cache_path(app_name: str) -> Path:
    return Path.home() / ".cache" / app_name


def _clear_dir(path: Path) -> int:
    count = 0
    for sub_path in path.iterdir():
        if sub_path.is_dir():
            count += _clear_dir(sub_path)
            sub_path.rmdir()
        else:
            sub_path.unlink()
            count += 1
    return count


def clear_directory(path: Path) -> int:
    CacheError.require_condition(path.exists(), f"Target {path=} does not exist")
    CacheError.require_condition(path.is_dir(), f"Target {path=} is not a directory")
    with CacheError.handle_errors(f"Failed to clear directory at {path=}"):
        return _clear_dir(path)


@dataclass
class CacheInfo:
    tree: Tree
    file_count: int
    total_size: int


def render_directory(path: Path, is_root: bool = True) -> CacheInfo:
    root_label: str
    if is_root:
        root_label = str(path)
        color = "[bold yellow]"
    else:
        root_label = escape(path.name)
        color = "[bold blue]"

    cache_info = CacheInfo(
        tree=Tree(f"{color}📂 {root_label}"),
        file_count=0,
        total_size=0,
    )

    child_paths = sorted(
        path.iterdir(),
        key=lambda p: (
            p.is_file(),
            p.name.lower(),
        ),
    )
    for child_path in child_paths:
        if child_path.is_dir():
            child_info = render_directory(child_path, is_root=False)
            cache_info.tree
            cache_info.tree.children.append(child_info.tree)
            cache_info.file_count += child_info.file_count
            cache_info.total_size += child_info.total_size
        else:
            file_size = child_path.stat().st_size
            icon = Text("📄 ")
            label = Text(escape(child_path.name), "green")
            info = Text(f" ({humanize.naturalsize(file_size)})", "blue")
            cache_info.tree.add(icon + label + info)
            cache_info.file_count += 1
            cache_info.total_size += file_size
    return cache_info


def is_child(path: Path, parent: Path):
    root_path = Path(path.parts[0])
    temp_path = path
    while temp_path != root_path:
        if temp_path == parent:
            return True
        temp_path = temp_path.parent
    return False


# TODO: add a mechanism to cleanup empty directories
class CacheManager:
    def __init__(self, app_name: str):
        self.app_name: str = app_name
        self.cache_path: Path = get_cache_path(self.app_name)
        with CacheInitError.handle_errors("Failed to initialize cache"):
            self.cache_path.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: Path | str, mkdir: bool = False) -> Path:
        if isinstance(path, str):
            path = Path(path)
        full_path = self.cache_path / path
        full_path = full_path.resolve()
        CacheError.require_condition(
            is_child(full_path, self.cache_path),
            f"Resolved cache path {str(full_path)} is not within cache {str(self.cache_path)}",
        )
        CacheError.require_condition(
            full_path != self.cache_path,
            f"Resolved cache path {str(full_path)} must not be the same as cache {str(self.cache_path)}",
        )
        if mkdir:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def store_bytes(self, data: bytes, path: Path | str, mode: int | None = None):
        full_path = self.resolve_path(path, mkdir=True)
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
        with CacheClearError.handle_errors(f"Failed to clear cache target {str(path)}"):
            full_path.unlink()
        if len([p for p in full_path.parent.iterdir()]) == 0:
            with CacheClearError.handle_errors(f"Failed to remove empty directory {str(full_path.parent)}"):
                full_path.parent.rmdir()
        return full_path

    def clear_all(self) -> int:
        with CacheClearError.handle_errors("Failed to clear cache"):
            return clear_directory(self.cache_path)

    def pretty(self) -> CacheInfo:
        return render_directory(self.cache_path)
