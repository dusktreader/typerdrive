from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar

import typer

from typerdrive.cache.exceptions import CacheError
from typerdrive.cache.manager import CacheManager
from typerdrive.cloaked import CloakingDevice
from typerdrive.context import from_context, to_context
from typerdrive.dirs import show_directory


def get_cache_manager(ctx: typer.Context) -> CacheManager:
    with CacheError.handle_errors("Cache is not bound to the context. Use the @attach_cache() decorator"):
        mgr: Any = from_context(ctx, "cache_manager")
    return CacheError.ensure_type(
        mgr,
        CacheManager,
        "Item in user context at `cache_manager` was not a CacheManager",
    )


P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def attach_cache(show: bool = False) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    def _decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        manager_param_key: str | None = None
        for key in func.__annotations__.keys():
            if func.__annotations__[key] is CacheManager:
                func.__annotations__[key] = Annotated[CacheManager | None, CloakingDevice]
                manager_param_key = key

        @wraps(func)
        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager: CacheManager = CacheManager()
            to_context(ctx, "cache_manager", manager)

            if manager_param_key:
                kwargs[manager_param_key] = manager

            ret_val = func(ctx, *args, **kwargs)

            if show:
                show_directory(manager.cache_dir, subject="Current cache")

            return ret_val

        return wrapper

    return _decorate
