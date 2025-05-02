from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar

import typer
from pydantic import BaseModel

from typerdrive.constants import Validation
from typerdrive.context import from_context, to_context, get_app_name
from typerdrive.format import terminal_message
from typerdrive.settings.exceptions import SettingsError
from typerdrive.settings.manager import SettingsManager


def get_settings[ST: BaseModel](ctx: typer.Context, type_hint: type[ST]) -> ST:
    return SettingsError.ensure_type(
        get_manager(ctx).settings_instance, type_hint, f"Settings instance doesn't match expected {type_hint=}"
    )


def get_manager(ctx: typer.Context) -> SettingsManager:
    return SettingsError.ensure_type(
        from_context(ctx, "settings_manager"),
        SettingsManager,
        "Item in user context at `settings_manager` was not a SettingsManager",
    )


P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def attach_settings(
    settings_model: type[BaseModel],
    *,
    validation: Validation = Validation.BEFORE,
    persist: bool = False,
    show: bool = False,
) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    def _decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        @wraps(func)
        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager: SettingsManager = SettingsManager(get_app_name(ctx), settings_model)

            if validation & Validation.BEFORE:
                SettingsError.require_condition(
                    len(manager.invalid_warnings) == 0,
                    f"Initial settings are invalid: {manager.invalid_warnings}",
                )
            to_context(ctx, "settings_manager", manager)

            ret_val = func(ctx, *args, **kwargs)

            if validation & Validation.AFTER:
                with SettingsError.handle_errors("Final settings are invalid"):
                    manager.validate()

            if persist:
                manager.save()
            if show:
                terminal_message(
                    manager.pretty(),
                    subject="Current settings",
                    footer=f"saved to {manager.settings_path}" if persist else None,
                )

            return ret_val

        return wrapper

    return _decorate
