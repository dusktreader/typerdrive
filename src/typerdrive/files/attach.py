"""
Provide a decorator that attaches the `typerdrive` files to a `typer` command function.
"""

from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar, cast

import typer

from typerdrive.files.exceptions import FilesError
from typerdrive.files.manager import FilesManager
from typerdrive.cloaked import CloakingDevice
from typerdrive.context import from_context, to_context
from typerdrive.dirs import show_directory


def get_files_manager(ctx: typer.Context) -> FilesManager:
    """
    Retrieve the `FilesManager` from the `TyperdriveContext`.
    """
    with FilesError.handle_errors("Files is not bound to the context. Use the @attach_files() decorator"):
        mgr: Any = from_context(ctx, "files_manager")
    return FilesError.ensure_type(
        mgr,
        FilesManager,
        "Item in user context at `files_manager` was not a FilesManager",
    )


P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def attach_files(show: bool = False) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    """
    Attach the `typerdrive` files to the decorated `typer` command function.

    Parameters:
        show: If set, show the files directory after the function runs.
    """

    def _decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        manager_param_key: str | None = None
        for key in func.__annotations__.keys():
            if func.__annotations__[key] is FilesManager:
                func.__annotations__[key] = Annotated[FilesManager | None, CloakingDevice]
                manager_param_key = key

        @wraps(func)
        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager: FilesManager = FilesManager()
            to_context(ctx, "files_manager", manager)

            if manager_param_key:
                kwargs_dict = cast(dict[str, Any], kwargs)
                kwargs_dict[manager_param_key] = manager

            ret_val = func(ctx, *args, **kwargs)

            if show:
                show_directory(manager.files_dir, subject="Current files")

            return ret_val

        return wrapper

    return _decorate
