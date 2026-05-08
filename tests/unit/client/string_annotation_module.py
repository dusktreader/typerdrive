# This module intentionally uses `from __future__ import annotations` so that
# all annotations are stored as strings rather than evaluated types.  This
# replicates the annotation-evaluation behaviour introduced in Python 3.14
# (PEP 649) and lets us test `attach_client` against string annotations on
# any supported Python version.
from __future__ import annotations

import typer
from pydantic import BaseModel
from typerdrive.client.attach import attach_client, get_client_manager
from typerdrive.client.base import TyperdriveClient
from typerdrive.client.manager import ClientManager
from typerdrive.settings.attach import attach_settings


class ClientSettings(BaseModel):
    url_base: str = "https://the.force.io"


def make_string_annotated_cli() -> typer.Typer:
    """
    Return a Typer app whose command function has string annotations.

    Because this module uses `from __future__ import annotations`, every type
    annotation in every function defined here is stored as a plain string in
    `__annotations__`.  Passing such a function to `attach_client` previously
    caused a `NameError` because the decorator compared raw annotation strings
    against type objects using `is`.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_client(jedi="https://the.force.io")
    def noop(ctx: typer.Context) -> None:
        manager = get_client_manager(ctx)
        assert len(manager.clients) == 1
        print("Passed!")

    return cli


def make_string_annotated_manager_cli() -> typer.Typer:
    """
    Return a Typer app whose command uses a `ClientManager` parameter with string annotations.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_client()
    def noop(ctx: typer.Context, mgr: ClientManager) -> None:
        assert isinstance(mgr, ClientManager)
        print("Passed!")

    return cli


def make_string_annotated_client_param_cli() -> typer.Typer:
    """
    Return a Typer app whose command uses a `TyperdriveClient` parameter with string annotations.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_settings(ClientSettings)
    @attach_client(jedi="url_base")
    def noop(ctx: typer.Context, jedi: TyperdriveClient) -> None:
        assert jedi is not None
        assert jedi.base_url == "https://the.force.io"
        print("Passed!")

    return cli
