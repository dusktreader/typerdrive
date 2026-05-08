"""
Provide a decorator that attaches the `typerdrive` cache to a `typer` command function.
"""

from collections.abc import Callable
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar, cast

import typer

from typerdrive.cache.exceptions import CacheError
from typerdrive.cache.manager import CacheManager
from typerdrive.cloaked import CloakingDevice
from typerdrive.context import from_context, to_context
from typerdrive.signature import SignatureRewriter


def get_cache_manager(ctx: typer.Context) -> CacheManager:
    """
    Retrieve the `CacheManager` from the `TyperdriveContext`.
    """
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
    """
    Attach the `typerdrive` cache to the decorated `typer` command function.

    Parameters:
        show: If set, show the cache after the function runs.
    """

    def _decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        manager_param_key: str | None = None
        rewriter = SignatureRewriter(func)
        for key, hint in rewriter.hints.items():
            if hint is CacheManager:
                rewriter.cloak(key, Annotated[CacheManager | None, CloakingDevice])
                manager_param_key = key

        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager: CacheManager = CacheManager()
            to_context(ctx, "cache_manager", manager)

            if manager_param_key:
                # ty: Cast kwargs to dict to allow mutation
                kwargs_dict = cast(dict[str, Any], kwargs)
                kwargs_dict[manager_param_key] = manager

            ret_val = func(ctx, *args, **kwargs)

            if show:
                manager.show(include_stats=False)

            return ret_val

        rewriter.apply(wrapper)
        return wrapper

    return _decorate
