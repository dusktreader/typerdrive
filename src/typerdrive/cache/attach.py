from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar

import humanize
import typer

from typerdrive.cache.exceptions import CacheError
from typerdrive.cache.manager import CacheManager
from typerdrive.context import from_context, to_context, get_app_name
from typerdrive.format import terminal_message


def get_manager(ctx: typer.Context) -> CacheManager:
    return CacheError.ensure_type(
        from_context(ctx, "cache_manager"),
        CacheManager,
        "Item in user context at `cache_manager` was not a CacheManager",
    )


P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def attach_cache(show: bool = False) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    def _decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        @wraps(func)
        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager: CacheManager = CacheManager(get_app_name(ctx))
            to_context(ctx, "cache_manager", manager)

            ret_val = func(ctx, *args, **kwargs)

            if show:
                cache_info = manager.pretty()
                human_size = humanize.naturalsize(cache_info.total_size)
                terminal_message(
                    cache_info.tree,
                    subject="Current cache",
                    footer=f"Storing {human_size} in {cache_info.file_count} files",
                )
            return ret_val

        return wrapper

    return _decorate
