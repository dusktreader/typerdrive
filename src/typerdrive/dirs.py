"""
Provide methods for working with directories.
"""

from dataclasses import dataclass
from pathlib import Path

import humanize
from rich.markup import escape
from rich.text import Text
from rich.tree import Tree

from typerdrive.exceptions import TyperdriveError
from typerdrive.format import terminal_message


def _clear_dir(path: Path) -> int:
    """
    INTERNAL FUNCTION: Should not be used externally.

    Used for recursively clearing a directory.
    """
    count = 0
    for sub_path in path.iterdir():
        if sub_path.is_symlink():
            sub_path.unlink()
            count += 1
        elif sub_path.is_dir():
            count += _clear_dir(sub_path)
            sub_path.rmdir()
        else:
            sub_path.unlink()
            count += 1
    return count


def clear_directory(path: Path) -> int:
    """
    Delete all files and directories in the directory at the given path.

    If the target path does not exist or is not a directory, an exception will be raised. A symlink supplied as the root
    path is followed to clear its target directory, and the root symlink is preserved. Symlinks found inside the target
    directory are unlinked without following them or modifying their targets.
    """
    TyperdriveError.require_condition(path.exists(), f"Target {path=} does not exist")
    TyperdriveError.require_condition(path.is_dir(), f"Target {path=} is not a directory")
    with TyperdriveError.handle_errors(f"Failed to clear directory at {path=}"):
        return _clear_dir(path)


@dataclass
class DirInfo:
    """
    Describes directory info needed for the `render_directory()` function.
    """

    tree: Tree
    file_count: int
    total_size: int


def render_directory(path: Path, is_root: bool = True) -> DirInfo:
    """
    Render a visualization of the directory at the given path using `rich.tree`.

    Omit symlink entries and never traverse their targets. Call this recursive function with `is_root=True`.
    """
    root_label: str
    if is_root:
        root_label = str(path)
        color = "[bold yellow]"
    else:
        root_label = escape(path.name)
        color = "[bold blue]"

    dir_info = DirInfo(
        tree=Tree(f"{color}📂 {root_label}"),
        file_count=0,
        total_size=0,
    )

    child_paths = sorted(
        (child_path for child_path in path.iterdir() if not child_path.is_symlink()),
        key=lambda p: (
            p.is_file(),
            p.name.lower(),
        ),
    )
    for child_path in child_paths:
        if child_path.is_dir():
            child_info = render_directory(child_path, is_root=False)
            dir_info.tree
            dir_info.tree.children.append(child_info.tree)
            dir_info.file_count += child_info.file_count
            dir_info.total_size += child_info.total_size
        else:
            file_size = child_path.stat().st_size
            icon = Text("📄 ")
            label = Text(escape(child_path.name), "green")
            info = Text(f" ({humanize.naturalsize(file_size)})", "blue")
            dir_info.tree.add(icon + label + info)
            dir_info.file_count += 1
            dir_info.total_size += file_size
    return dir_info


def show_directory(path: Path, subject: str | None = None):
    """
    Print a directory visualization using `terminal_message`.

    Symlink entries and their targets are omitted, as in `render_directory()`.
    """
    dir_info = render_directory(path)
    human_size = humanize.naturalsize(dir_info.total_size)
    terminal_message(
        dir_info.tree,
        subject=subject or f"Showing {path}",
        footer=f"Storing {human_size} in {dir_info.file_count} files",
    )


def is_child(path: Path, parent: Path) -> bool:
    """
    Return true if the given path is a child of the given parent.

    Both paths are resolved to handle symlinks before comparison.
    """
    # Resolve both paths to handle symlinks (e.g., /var -> /private/var on macOS)
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()

    root_path = Path(resolved_path.parts[0])
    temp_path = resolved_path
    while temp_path != root_path:
        if temp_path == resolved_parent:
            return True
        temp_path = temp_path.parent
    return False
