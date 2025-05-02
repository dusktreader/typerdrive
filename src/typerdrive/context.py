from dataclasses import dataclass
from typing import cast, get_origin, get_args
from types import NoneType, UnionType

from buzz import require_condition
import typer

from typerdrive.cache.manager import CacheManager
from typerdrive.exceptions import ContextError
from typerdrive.settings.manager import SettingsManager


@dataclass
class TyperdriveContext:
    settings_manager: SettingsManager | None = None
    cache_manager: CacheManager | None = None


def get_user_context(ctx: typer.Context):
    if not ctx.obj:
        ctx.obj = TyperdriveContext()
    return ctx.obj


def to_context(ctx: typer.Context, name: str, val: SettingsManager | CacheManager):
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


def from_context(ctx: typer.Context, name: str) -> SettingsManager | CacheManager:
    user_context = get_user_context(ctx)
    return ContextError.enforce_defined(getattr(user_context, name), f"{name} is not bound to context")


def get_app_name(ctx: typer.Context) -> str:
    if ctx.parent:
        return get_app_name(cast(typer.Context, ctx.parent))
    return ContextError.enforce_defined(ctx.info_name, "typerdrive requires the app to have a name")
