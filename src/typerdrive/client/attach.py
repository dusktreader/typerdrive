from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar

import typer
from pydantic import BaseModel

from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError
from typerdrive.client.manager import ClientManager, ClientSpec
from typerdrive.cloaked import CloakingDevice
from typerdrive.context import from_context, to_context
from typerdrive.settings.attach import get_settings_manager
from typerdrive.settings.exceptions import SettingsError


def get_client_manager(ctx: typer.Context) -> ClientManager:
    with ClientError.handle_errors("Client(s) are not bound to the context. Use the @attach_client() decorator"):
        mgr: Any = from_context(ctx, "client_manager")
    return ClientError.ensure_type(
        mgr,
        ClientManager,
        "Item in user context at `client_manager` was not a ClientManager",
    )


def get_client(ctx: typer.Context, name: str) -> TyperdriveClient:
    return get_client_manager(ctx).get_client(name)


P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def attach_client(**client_urls_or_settings_keys: str) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    def _decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        manager_param_key: str | None = None
        client_param_keys: list[str] = []
        for key in func.__annotations__.keys():
            if func.__annotations__[key] is TyperdriveClient:
                if key in client_urls_or_settings_keys:
                    func.__annotations__[key] = Annotated[TyperdriveClient | None, CloakingDevice]
                    client_param_keys.append(key)

            elif func.__annotations__[key] is ClientManager:
                func.__annotations__[key] = Annotated[ClientManager | None, CloakingDevice]
                manager_param_key = key

        @wraps(func)
        def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs) -> T:
            manager = ClientManager()

            settings: BaseModel | None
            try:
                settings = get_settings_manager(ctx).settings_instance
            except SettingsError:
                settings = None

            for name, url_or_settings_key in client_urls_or_settings_keys.items():
                base_url: str = getattr(settings, url_or_settings_key, url_or_settings_key)
                with ClientError.handle_errors(
                    f"Couldn't use {base_url=} for client. If using a settings key, make sure settings are attached."
                ):
                    client_spec = ClientSpec(base_url=base_url)
                manager.add_client(name, client_spec)

            to_context(ctx, "client_manager", manager)

            for key in client_param_keys:
                kwargs[key] = manager.get_client(key)

            if manager_param_key:
                kwargs[manager_param_key] = manager

            return func(ctx, *args, **kwargs)

        return wrapper

    return _decorate
