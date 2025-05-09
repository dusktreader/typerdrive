from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar

import typer
from loguru import logger

from typerdrive.cloaked import CloakingDevice
from typerdrive.context import from_context, to_context
from typerdrive.logging.exceptions import LoggingError
from typerdrive.logging.manager import LoggingManager


def get_logging_manager(ctx: typer.Context) -> LoggingManager:
    with LoggingError.handle_errors("Logging is not bound to the context. Use the @attach_logging() decorator"):
        mgr: Any = from_context(ctx, "logging_manager")
    return LoggingError.ensure_type(
        mgr,
        LoggingManager,
        "Item in user context at `logging_manager` was not a LoggingManager",
    )


P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def attach_logging(verbose: bool = False) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    def _decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        manager_param_key: str | None = None
        for key in func.__annotations__.keys():
            if func.__annotations__[key] is LoggingManager:
                func.__annotations__[key] = Annotated[LoggingManager | None, CloakingDevice]
                manager_param_key = key

        @wraps(func)
        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager: LoggingManager = LoggingManager(verbose=verbose)
            to_context(ctx, "logging_manager", manager)

            logger.debug("Logging attached to typer context")

            if manager_param_key:
                kwargs[manager_param_key] = manager

            return func(ctx, *args, **kwargs)

        return wrapper

    return _decorate
