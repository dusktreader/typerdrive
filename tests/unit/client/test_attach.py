import typer
from pydantic import BaseModel
from typerdrive.client.attach import attach_client, get_client_manager
from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError
from typerdrive.client.manager import ClientManager
from typerdrive.settings.attach import attach_settings

from tests.unit.client.string_annotation_module import (
    make_string_annotated_cli,
    make_string_annotated_client_param_cli,
    make_string_annotated_manager_cli,
)
from tests.unit.helpers import check_output, match_output


class ClientSettings(BaseModel):
    url_base: str = "https://the.force.io"


class TestAttachClient:
    def test_attach_client__adds_client_manager_to_context(self):
        cli = typer.Typer()

        @cli.command()
        @attach_client()
        def noop(ctx: typer.Context):
            manager = get_client_manager(ctx)
            assert isinstance(manager, ClientManager)
            assert manager.clients == {}
            print("Passed!")

        check_output(cli, prog_name="test", expected_substring="Passed!")

    def test_attach_client__adds_a_client_using_explicit_base_url(self):
        cli = typer.Typer()

        @cli.command()
        @attach_client(jedi="https://the.force.io")
        def noop(ctx: typer.Context):
            manager = get_client_manager(ctx)
            assert len(manager.clients) == 1
            client = manager.clients.get("jedi")
            assert client is not None
            assert client.base_url == "https://the.force.io"
            print("Passed!")

        check_output(cli, prog_name="test", expected_substring="Passed!")

    def test_attach_client__adds_a_client_with_base_url_from_settings(self):
        cli = typer.Typer()

        @cli.command()
        @attach_settings(ClientSettings)
        @attach_client(jedi="url_base")
        def noop(ctx: typer.Context):
            manager = get_client_manager(ctx)
            assert len(manager.clients) == 1
            client = manager.clients.get("jedi")
            assert client is not None
            assert client.base_url == "https://the.force.io"
            print("Passed!")

        check_output(cli, prog_name="test", expected_substring="Passed!")

    def test_attach_client__raises_an_error_if_invalid_url(self):
        cli = typer.Typer()

        @cli.command()
        @attach_settings(ClientSettings)
        @attach_client(jedi="not-a-url")
        def noop(ctx: typer.Context):
            get_client_manager(ctx)
            print("We should never get here")

        match_output(
            cli,
            unwanted_pattern="We should never get here",
            exception_type=ClientError,
            exception_pattern=r"Couldn't use base_url='not-a-url' for client",
            exit_code=1,
            prog_name="test",
        )

    def test_attach_client__adds_multiple_clients(self):
        cli = typer.Typer()

        @cli.command()
        @attach_settings(ClientSettings)
        @attach_client(sith="https://the.dark.side", jedi="url_base")
        def noop(ctx: typer.Context):
            manager = get_client_manager(ctx)
            assert len(manager.clients) == 2

            sith_client = manager.clients.get("sith")
            assert sith_client is not None
            assert sith_client.base_url == "https://the.dark.side"

            jedi_client = manager.clients.get("jedi")
            assert jedi_client is not None
            assert jedi_client.base_url == "https://the.force.io"
            print("Passed!")

        check_output(cli, prog_name="test", expected_substring="Passed!")


class TestWithParameters:
    def test_attach_client__with_manager_parameter(self):
        cli = typer.Typer()

        @cli.command()
        @attach_client()
        def noop(ctx: typer.Context, mgr: ClientManager):
            assert isinstance(mgr, ClientManager)
            assert mgr.clients == {}
            print("Passed!")

        check_output(cli, prog_name="test", expected_substring="Passed!")

    def test_attach_client__with_client_parameters(self):
        cli = typer.Typer()

        @cli.command()
        @attach_settings(ClientSettings)
        @attach_client(sith="https://the.dark.side", jedi="url_base")
        def noop(ctx: typer.Context, jedi: TyperdriveClient, sith: TyperdriveClient):
            assert sith is not None
            assert sith.base_url == "https://the.dark.side"

            assert jedi is not None
            assert jedi.base_url == "https://the.force.io"
            print("Passed!")

        check_output(cli, prog_name="test", expected_substring="Passed!")


class TestGetManager:
    def test_get_client_manager__extracts_client_manager_from_context(self):
        cli = typer.Typer()

        @cli.command()
        @attach_client()
        def noop(ctx: typer.Context):
            manager = get_client_manager(ctx)
            assert isinstance(manager, ClientManager)
            assert manager.clients == {}
            print("Passed!")

        check_output(cli, prog_name="test", expected_substring="Passed!")

    def test_get_client_manager__raises_exception_if_context_has_no_manager(self):
        cli = typer.Typer()

        @cli.command()
        def noop(ctx: typer.Context):
            get_client_manager(ctx)
            print("Passed!")

        match_output(
            cli,
            exception_type=ClientError,
            exception_pattern=r"Client\(s\) are not bound to the context",
            escape_parens=True,
            exit_code=1,
            prog_name="test",
        )

    def test_get_client_manager__raises_exception_if_non_manager_retrieved(self):
        cli = typer.Typer()

        @cli.command()
        @attach_client()
        def noop(ctx: typer.Context):
            ctx.obj.client_manager = "Not a manager!"
            get_client_manager(ctx)
            print("Passed!")

        match_output(
            cli,
            exception_type=ClientError,
            exception_pattern="Item in user context at `client_manager` was not a ClientManager",
            exit_code=1,
            prog_name="test",
        )


class TestStringAnnotations:
    """
    Verify that `attach_client` works correctly when the decorated function
    stores its annotations as strings rather than resolved types.

    This happens in any module that uses `from __future__ import annotations`
    (all Python versions) and is the default behaviour in Python 3.14+ (PEP 649).
    Previously, the decorator compared raw `__annotations__` values against type
    objects using `is`, which always failed for string annotations and could raise
    a `NameError` when Python's machinery tried to resolve the strings.
    """

    def test_client_attached_with_string_annotations(self):
        """Client manager is attached correctly when annotations are strings."""
        cli = make_string_annotated_cli()

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )

    def test_manager_parameter_injected_with_string_annotations(self):
        """ClientManager parameter is injected correctly when annotations are strings."""
        cli = make_string_annotated_manager_cli()

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )

    def test_client_parameter_injected_with_string_annotations(self):
        """TyperdriveClient parameter is injected correctly when annotations are strings."""
        cli = make_string_annotated_client_param_cli()

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )
