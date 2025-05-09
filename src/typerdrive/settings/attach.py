from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar

import typer
from pydantic import BaseModel
from typer_repyt.constants import Sentinel

from typerdrive.cloaked import CloakingDevice
from typerdrive.constants import Validation
from typerdrive.context import from_context, to_context
from typerdrive.format import terminal_message
from typerdrive.settings.exceptions import SettingsError
from typerdrive.settings.manager import SettingsManager


def get_settings[ST: BaseModel](
    ctx: typer.Context,
    type_hint: type[ST],
) -> ST:
    return SettingsError.ensure_type(
        get_settings_manager(ctx).settings_instance,
        type_hint,
        f"Settings instance doesn't match expected {type_hint=}",
    )


def get_settings_value(ctx: typer.Context, settings_key: str) -> Any:
    instance: BaseModel = get_settings_manager(ctx).settings_instance
    ret = getattr(instance, settings_key, Sentinel.MISSING)
    SettingsError.require_condition(
        ret is not Sentinel.MISSING,
        f"Settings instance doesn't have field {settings_key}",
    )
    return ret


def get_settings_manager(ctx: typer.Context) -> SettingsManager:
    with SettingsError.handle_errors("Settings are not bound to the context. Use the @attach_settings() decorator"):
        mgr: Any = from_context(ctx, "settings_manager")
    return SettingsError.ensure_type(
        mgr,
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
        manager_param_key: str | None = None
        settings_param_key: str | None = None
        for key in func.__annotations__.keys():
            if func.__annotations__[key] is settings_model:
                func.__annotations__[key] = Annotated[settings_model | None, CloakingDevice]
                settings_param_key = key
            elif func.__annotations__[key] is SettingsManager:
                func.__annotations__[key] = Annotated[SettingsManager | None, CloakingDevice]
                manager_param_key = key

        # TODO: Figure out how we can make the ctx param optional for the wrapped function
        @wraps(func)
        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager: SettingsManager = SettingsManager(settings_model)

            if validation & Validation.BEFORE:
                SettingsError.require_condition(
                    len(manager.invalid_warnings) == 0,
                    f"Initial settings are invalid: {manager.invalid_warnings}",
                )
            to_context(ctx, "settings_manager", manager)

            if settings_param_key:
                kwargs[settings_param_key] = manager.settings_instance

            if manager_param_key:
                kwargs[manager_param_key] = manager

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
