"""
Step definitions for the client BDD feature.

Each scenario drives a real typer.Typer() app assembled inline with
the typerdrive client decorators, then invokes it through typer's CliRunner.
"""

import json

import httpx
import pytest
import respx
import typer
from click.testing import Result
from pydantic import BaseModel
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from typerdrive.client.attach import attach_client, get_client, get_client_manager
from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError
from typerdrive.config import get_typerdrive_config
from typerdrive.handle_errors import handle_errors
from typerdrive.settings.attach import attach_settings


# ---------------------------------------------------------------------------
# Settings model for client scenarios that need settings
# ---------------------------------------------------------------------------


class ClientSettings(BaseModel):
    base_url: str = "https://the.force.io"


# ---------------------------------------------------------------------------
# Scenario bindings
# ---------------------------------------------------------------------------


@scenario("../features/client.feature", "Attach client with explicit base URL")
def test_attach_client_with_explicit_base_url():
    pass


@scenario("../features/client.feature", "Attach client with base URL from settings")
def test_attach_client_with_base_url_from_settings():
    pass


@scenario("../features/client.feature", "Attach multiple clients")
def test_attach_multiple_clients():
    pass


@scenario("../features/client.feature", "Client is accessible as a command parameter")
def test_client_accessible_as_parameter():
    pass


@scenario("../features/client.feature", "Attach client fails with invalid URL")
def test_attach_client_fails_with_invalid_url():
    pass


@scenario("../features/client.feature", "Client makes a successful GET request")
def test_client_makes_successful_get_request():
    pass


# ---------------------------------------------------------------------------
# Shared state container
# ---------------------------------------------------------------------------


class ClientContext:
    cli: typer.Typer
    result: Result
    base_urls: dict[str, str]  # name -> url captured inside command


@pytest.fixture
def ctx() -> ClientContext:
    c = ClientContext()
    c.base_urls = {}
    return c


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("a CLI app with a mock HTTP server")
def _given_cli_app(ctx: ClientContext):
    ctx.cli = typer.Typer()


@given(parsers.parse('settings with base_url "{url}"'))
def _given_settings_with_base_url(url: str):
    settings_path = get_typerdrive_config().settings_path
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"base_url": url}))


@given(parsers.parse('a mock server at "{base_url}" returning {json_body}'))
def _given_mock_server(ctx: ClientContext, base_url: str, json_body: str, respx_mock: respx.MockRouter):
    data = json.loads(json_body)
    respx_mock.get(f"{base_url}/person").mock(return_value=httpx.Response(200, json=data))
    ctx.base_urls["mock_server"] = base_url


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(parsers.parse('a command attaches a client named "{name}" with base URL "{url}"'))
def _when_attach_client_explicit_url(ctx: ClientContext, runner: CliRunner, name: str, url: str):
    client_kwargs = {name: url}
    _captured: dict[str, str] = {}

    @ctx.cli.command()
    @attach_client(**client_kwargs)
    def _run(ctx: typer.Context):
        manager = get_client_manager(ctx)
        client = manager.get_client(name)
        _captured[name] = str(client.base_url)
        print(f"client {name} ready")

    ctx.result = runner.invoke(ctx.cli, [], prog_name="test")
    ctx.base_urls.update(_captured)


@when(parsers.parse('a command attaches a client named "{name}" using settings key "{key}"'))
def _when_attach_client_from_settings(ctx: ClientContext, runner: CliRunner, name: str, key: str):
    client_kwargs = {name: key}
    _captured: dict[str, str] = {}

    @ctx.cli.command()
    @attach_settings(ClientSettings)
    @attach_client(**client_kwargs)
    def _run(ctx: typer.Context):
        manager = get_client_manager(ctx)
        client = manager.get_client(name)
        _captured[name] = str(client.base_url)
        print(f"client {name} ready")

    ctx.result = runner.invoke(ctx.cli, [], prog_name="test")
    ctx.base_urls.update(_captured)


@when(parsers.parse('a command attaches clients "{name1}" at "{url1}" and "{name2}" at "{url2}"'))
def _when_attach_multiple_clients(ctx: ClientContext, runner: CliRunner, name1: str, url1: str, name2: str, url2: str):
    client_kwargs = {name1: url1, name2: url2}
    _captured: dict[str, str] = {}

    @ctx.cli.command()
    @attach_client(**client_kwargs)
    def _run(ctx: typer.Context):
        manager = get_client_manager(ctx)
        for n in (name1, name2):
            client = manager.get_client(n)
            _captured[n] = str(client.base_url)
        print("clients ready")

    ctx.result = runner.invoke(ctx.cli, [], prog_name="test")
    ctx.base_urls.update(_captured)


@when(parsers.parse('a command receives the client "{name}" at "{url}" as a parameter'))
def _when_client_as_parameter(ctx: ClientContext, runner: CliRunner, name: str, url: str):
    client_kwargs = {name: url}
    _captured: dict[str, str] = {}

    @ctx.cli.command()
    @attach_client(**client_kwargs)
    def _run(ctx: typer.Context, jedi: TyperdriveClient):
        _captured[name] = str(jedi.base_url)
        print("client ready")

    ctx.result = runner.invoke(ctx.cli, [], prog_name="test")
    ctx.base_urls.update(_captured)


@when(parsers.parse('a command tries to attach a client with an invalid URL "{url}"'))
def _when_attach_client_invalid_url(ctx: ClientContext, runner: CliRunner, url: str):
    client_kwargs = {"broken": url}

    @ctx.cli.command()
    @handle_errors("Failed to attach client", handle_exc_class=ClientError)
    @attach_client(**client_kwargs)
    def _run(ctx: typer.Context):
        print("should not reach here")

    ctx.result = runner.invoke(ctx.cli, [], prog_name="test")


@when(parsers.parse('a command uses the client to GET "{endpoint}"'))
def _when_client_get(ctx: ClientContext, runner: CliRunner, endpoint: str):
    base_url = ctx.base_urls.get("mock_server", "https://swapi.test")

    @ctx.cli.command()
    @attach_client(api=base_url)
    def _run(ctx: typer.Context):
        client = get_client(ctx, "api")
        response = client.request_x("GET", endpoint)
        print(json.dumps(response))

    ctx.result = runner.invoke(ctx.cli, [], prog_name="test")


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the command succeeds")
def _then_command_succeeds(ctx: ClientContext):
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}\n"
        f"Exception: {ctx.result.exception}\n"
        f"Output:\n{ctx.result.output}"
    )


@then(parsers.parse("the command fails with exit code {code:d}"))
def _then_command_fails(ctx: ClientContext, code: int):
    assert ctx.result.exit_code == code, (
        f"Expected exit code {code}, got {ctx.result.exit_code}\nOutput:\n{ctx.result.output}"
    )


@then(parsers.parse('the output contains "{text}"'))
def _then_output_contains(ctx: ClientContext, text: str):
    assert text in ctx.result.output, f"Expected {text!r} in output.\nActual output:\n{ctx.result.output}"


@then(parsers.parse('the client "{name}" has base URL "{url}"'))
def _then_client_has_base_url(ctx: ClientContext, name: str, url: str):
    actual = ctx.base_urls.get(name)
    assert actual is not None, f"No base URL captured for client {name!r}"
    assert actual == url, f"Expected base URL {url!r} for {name!r}, got {actual!r}"
