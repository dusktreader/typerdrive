"""
Step definitions for the files BDD feature.

Each scenario drives a real typer.Typer() app assembled inline with
the typerdrive files decorators/commands, then invokes it through
typer's CliRunner.
"""

import json
from pathlib import Path

import pytest
import typer
from click.testing import Result
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from typerdrive.config import get_typerdrive_config
from typerdrive.files.attach import attach_files, get_files_manager
from typerdrive.files.commands import add_files_subcommand
from typerdrive.files.manager import FilesManager


# ---------------------------------------------------------------------------
# Scenario bindings
# ---------------------------------------------------------------------------


@scenario("../features/files.feature", "Store text file via attach_files decorator")
def test_store_text_file():
    pass


@scenario("../features/files.feature", "Store JSON data via attach_files decorator")
def test_store_json_data():
    pass


@scenario("../features/files.feature", "Store binary data via attach_files decorator")
def test_store_binary_data():
    pass


@scenario("../features/files.feature", "Load text file via attach_files decorator")
def test_load_text_file():
    pass


@scenario("../features/files.feature", "Load JSON data via attach_files decorator")
def test_load_json_data():
    pass


@scenario("../features/files.feature", "Files show command displays stored files")
def test_files_show_displays_stored_files():
    pass


@scenario("../features/files.feature", "Files manager is accessible via context")
def test_files_manager_accessible_via_context():
    pass


# ---------------------------------------------------------------------------
# Shared state container
# ---------------------------------------------------------------------------


class FilesContext:
    cli: typer.Typer
    result: Result


@pytest.fixture
def ctx() -> FilesContext:
    return FilesContext()


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("a CLI app with files subcommand")
def _given_cli_with_files_subcommand(ctx: FilesContext):
    ctx.cli = typer.Typer()
    add_files_subcommand(ctx.cli)


@given(parsers.parse('the file "{path}" contains pre-stored text "{text}"'))
def _given_file_contains_text(path: str, text: str):
    files_dir = get_typerdrive_config().files_dir
    full_path = files_dir / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(text)


@given(parsers.parse('the file "{path}" contains pre-stored JSON with key "{key}" equal to "{value}"'))
def _given_file_contains_json(path: str, key: str, value: str):
    files_dir = get_typerdrive_config().files_dir
    full_path = files_dir / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(json.dumps({key: value}))


# ---------------------------------------------------------------------------
# When steps — inline CLI commands assembled per step
# ---------------------------------------------------------------------------


@when(parsers.parse('a command stores text "{text}" at path "{path}"'))
def _when_store_text(ctx: FilesContext, runner: CliRunner, text: str, path: str):
    @ctx.cli.command("store-text")
    @attach_files()
    def _store_text(ctx: typer.Context):
        manager = get_files_manager(ctx)
        manager.store_text(text, path)
        print(f"stored {path}")

    ctx.result = runner.invoke(ctx.cli, ["store-text"], prog_name="test")


@when(parsers.parse('a command stores JSON with planet "{planet}" and moons {moons:d} at path "{path}"'))
def _when_store_json(ctx: FilesContext, runner: CliRunner, planet: str, moons: int, path: str):
    @ctx.cli.command("store-json")
    @attach_files()
    def _store_json(ctx: typer.Context):
        manager = get_files_manager(ctx)
        manager.store_json({"planet": planet, "moons": moons}, path)
        print(f"stored {path}")

    ctx.result = runner.invoke(ctx.cli, ["store-json"], prog_name="test")


@when(parsers.parse('a command stores bytes at path "{path}"'))
def _when_store_bytes(ctx: FilesContext, runner: CliRunner, path: str):
    @ctx.cli.command("store-bytes")
    @attach_files()
    def _store_bytes(ctx: typer.Context):
        manager = get_files_manager(ctx)
        manager.store_bytes(b"\x00\x01\x02\x03", path)
        print(f"stored {path}")

    ctx.result = runner.invoke(ctx.cli, ["store-bytes"], prog_name="test")


@when(parsers.parse('a command loads and prints text from "{path}"'))
def _when_load_text(ctx: FilesContext, runner: CliRunner, path: str):
    @ctx.cli.command("load-text")
    @attach_files()
    def _load_text(ctx: typer.Context):
        manager = get_files_manager(ctx)
        content = manager.load_text(path)
        print(content)

    ctx.result = runner.invoke(ctx.cli, ["load-text"], prog_name="test")


@when(parsers.parse('a command loads and prints JSON from "{path}"'))
def _when_load_json(ctx: FilesContext, runner: CliRunner, path: str):
    @ctx.cli.command("load-json")
    @attach_files()
    def _load_json(ctx: typer.Context):
        manager = get_files_manager(ctx)
        data = manager.load_json(path)
        print(json.dumps(data))

    ctx.result = runner.invoke(ctx.cli, ["load-json"], prog_name="test")


@when("I run the files show command")
def _when_files_show(ctx: FilesContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["files", "show"], prog_name="test")


@when("a command accesses the files manager through the typer context")
def _when_access_manager_via_context(ctx: FilesContext, runner: CliRunner):
    @ctx.cli.command("get-manager")
    @attach_files()
    def _get_manager(ctx: typer.Context):
        manager = get_files_manager(ctx)
        assert isinstance(manager, FilesManager)
        print("manager retrieved")

    ctx.result = runner.invoke(ctx.cli, ["get-manager"], prog_name="test")


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the command succeeds")
def _then_command_succeeds(ctx: FilesContext):
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}\n"
        f"Exception: {ctx.result.exception}\n"
        f"Output:\n{ctx.result.output}"
    )


@then(parsers.parse("the command fails with exit code {code:d}"))
def _then_command_fails(ctx: FilesContext, code: int):
    assert ctx.result.exit_code == code, (
        f"Expected exit code {code}, got {ctx.result.exit_code}\nOutput:\n{ctx.result.output}"
    )


@then(parsers.parse('the output contains "{text}"'))
def _then_output_contains(ctx: FilesContext, text: str):
    assert text in ctx.result.output, f"Expected {text!r} in output.\nActual output:\n{ctx.result.output}"


@then(parsers.parse('the file "{path}" exists in the files directory'))
def _then_file_exists(path: str):
    files_dir = get_typerdrive_config().files_dir
    full_path = files_dir / path
    assert full_path.exists(), f"Expected file {full_path} to exist"


@then(parsers.parse('the file "{path}" contains text "{text}"'))
def _then_file_contains_text(path: str, text: str):
    files_dir = get_typerdrive_config().files_dir
    full_path = files_dir / path
    assert full_path.exists(), f"File {full_path} does not exist"
    assert full_path.read_text() == text, f"Expected text {text!r}, got {full_path.read_text()!r}"


@then(parsers.parse('the file "{path}" contains JSON with key "{key}" equal to "{value}"'))
def _then_file_contains_json_key(path: str, key: str, value: str):
    files_dir = get_typerdrive_config().files_dir
    full_path = files_dir / path
    assert full_path.exists(), f"File {full_path} does not exist"
    data = json.loads(full_path.read_text())
    assert str(data.get(key)) == value, f"Expected {key}={value!r}, got {data.get(key)!r}"
