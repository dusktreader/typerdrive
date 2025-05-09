from dataclasses import dataclass
from types import NoneType, UnionType
from typing import get_args, get_origin

import typer
from buzz import require_condition

from typerdrive.cache.manager import CacheManager
from typerdrive.client.manager import ClientManager
from typerdrive.exceptions import ContextError
from typerdrive.logging.manager import LoggingManager
from typerdrive.settings.manager import SettingsManager

type TyperdriveManager = SettingsManager | CacheManager | ClientManager | LoggingManager


@dataclass
class TyperdriveContext:
    settings_manager: SettingsManager | None = None
    cache_manager: CacheManager | None = None
    client_manager: ClientManager | None = None
    logging_manager: LoggingManager | None = None


def get_user_context(ctx: typer.Context):
    if not ctx.obj:
        ctx.obj = TyperdriveContext()
    return ctx.obj


def to_context(ctx: typer.Context, name: str, val: TyperdriveManager) -> None:
    user_context = get_user_context(ctx)
    field_type = TyperdriveContext.__dataclass_fields__[name].type

    if get_origin(field_type) is UnionType:
        defined_types = [t for t in get_args(field_type) if t is not NoneType]
        require_condition(
            len(defined_types) == 1,
            "PANIC! TyperdriveContext fields must only have one type or None.",
            raise_exc_class=RuntimeError,
        )
        field_type = defined_types[0]

    # TODO: Get the type hinting on the next line right.
    ContextError.ensure_type(val, field_type, "Value is not of type any of the union types")  # type: ignore[arg-type]

    setattr(user_context, name, val)


def from_context(ctx: typer.Context, name: str) -> TyperdriveManager:
    user_context = get_user_context(ctx)
    return ContextError.enforce_defined(getattr(user_context, name), f"{name} is not bound to context")
