"""
Step definitions for the settings BDD feature.

Each scenario drives a real typer.Typer() app assembled inline with
the typerdrive settings decorators/commands, then invokes it through
typer's CliRunner — the same approach as the existing unit tests.
"""

import json
from pathlib import Path

import pytest
import typer
from click.testing import Result
from pydantic import BaseModel, field_validator
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from typerdrive.config import get_typerdrive_config
from typerdrive.settings.commands import (
    add_reset,
    add_settings_subcommand,
    add_show,
    add_unset,
    add_update,
)
from typerdrive.settings.commands import add_bind as _add_bind


# ---------------------------------------------------------------------------
# Settings model shared across all settings scenarios
# ---------------------------------------------------------------------------


class ScenarioSettings(BaseModel):
    name: str
    planet: str
    is_humanoid: bool = True
    alignment: str = "neutral"

    @field_validator("alignment")
    @classmethod
    def _validate_alignment(cls, v: str) -> str:
        allowed = {"neutral", "good", "evil"}
        if v not in allowed:
            raise ValueError(f"{v} is an invalid alignment")
        return v


# ---------------------------------------------------------------------------
# Scenario bindings
# ---------------------------------------------------------------------------


@scenario("../features/settings.feature", "Bind saves all required fields to disk")
def test_bind_saves_all_required_fields_to_disk():
    pass


@scenario("../features/settings.feature", "Bind fails when required fields are missing")
def test_bind_fails_when_required_fields_are_missing():
    pass


@scenario("../features/settings.feature", "Update saves partial fields without failing on missing required fields")
def test_update_saves_partial_fields():
    pass


@scenario("../features/settings.feature", "Unset resets a field to its default value")
def test_unset_resets_a_field_to_its_default():
    pass


@scenario("../features/settings.feature", "Unset can leave settings in an invalid state")
def test_unset_can_leave_invalid_state():
    pass


@scenario("../features/settings.feature", "Show displays current settings values")
def test_show_displays_current_settings():
    pass


@scenario("../features/settings.feature", "Reset clears all settings back to defaults after confirmation")
def test_reset_clears_settings_after_confirmation():
    pass


@scenario("../features/settings.feature", "Reset is cancelled when confirmation is denied")
def test_reset_is_cancelled_when_denied():
    pass


# ---------------------------------------------------------------------------
# Shared state container
# ---------------------------------------------------------------------------


class SettingsContext:
    cli: typer.Typer
    result: Result
    settings_path: Path


@pytest.fixture
def ctx() -> SettingsContext:
    return SettingsContext()


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("a CLI app with settings subcommand")
def _given_cli_with_settings_subcommand(ctx: SettingsContext):
    ctx.cli = typer.Typer()
    add_settings_subcommand(ctx.cli, ScenarioSettings)


@given(
    parsers.parse('the settings file has name "{name}", planet "{planet}", is_humanoid true, alignment "{alignment}"')
)
def _given_settings_file_with_truthy_humanoid(
    ctx: SettingsContext,
    name: str,
    planet: str,
    alignment: str,
):
    settings_path = get_typerdrive_config().settings_path
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(
            dict(
                name=name,
                planet=planet,
                is_humanoid=True,
                alignment=alignment,
            )
        )
    )
    ctx.settings_path = settings_path


@given(
    parsers.parse('the settings file has name "{name}", planet "{planet}", is_humanoid false, alignment "{alignment}"')
)
def _given_settings_file_with_falsy_humanoid(
    ctx: SettingsContext,
    name: str,
    planet: str,
    alignment: str,
):
    settings_path = get_typerdrive_config().settings_path
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(
            dict(
                name=name,
                planet=planet,
                is_humanoid=False,
                alignment=alignment,
            )
        )
    )
    ctx.settings_path = settings_path


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(parsers.parse('I run the settings bind command with "{arg1}" and "{arg2}"'))
def _when_bind_with_two_args(ctx: SettingsContext, runner: CliRunner, arg1: str, arg2: str):
    ctx.result = runner.invoke(ctx.cli, ["settings", "bind", arg1, arg2], prog_name="test")


@when(parsers.parse('I run the settings bind command with "{arg1}" only'))
def _when_bind_with_one_arg(ctx: SettingsContext, runner: CliRunner, arg1: str):
    ctx.result = runner.invoke(ctx.cli, ["settings", "bind", arg1], prog_name="test")


@when(parsers.parse('I run the settings update command with "{arg1}"'))
def _when_update_with_one_arg(ctx: SettingsContext, runner: CliRunner, arg1: str):
    ctx.result = runner.invoke(ctx.cli, ["settings", "update", arg1], prog_name="test")


@when(parsers.parse('I run the settings unset command with "{arg1}"'))
def _when_unset_with_one_arg(ctx: SettingsContext, runner: CliRunner, arg1: str):
    ctx.result = runner.invoke(ctx.cli, ["settings", "unset", arg1], prog_name="test")


@when(parsers.parse('I run the settings unset command with "{arg1}" and "{arg2}"'))
def _when_unset_with_two_args(ctx: SettingsContext, runner: CliRunner, arg1: str, arg2: str):
    ctx.result = runner.invoke(ctx.cli, ["settings", "unset", arg1, arg2], prog_name="test")


@when("I run the settings show command")
def _when_show(ctx: SettingsContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["settings", "show"], prog_name="test")


@when(parsers.parse('I run the settings reset command and confirm with "{answer}"'))
def _when_reset_with_confirmation(ctx: SettingsContext, runner: CliRunner, answer: str):
    ctx.result = runner.invoke(ctx.cli, ["settings", "reset"], input=answer, prog_name="test")


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the command succeeds")
def _then_command_succeeds(ctx: SettingsContext):
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}\n"
        f"Exception: {ctx.result.exception}\n"
        f"Output:\n{ctx.result.output}"
    )


@then(parsers.parse("the command fails with exit code {code:d}"))
def _then_command_fails(ctx: SettingsContext, code: int):
    assert ctx.result.exit_code == code, (
        f"Expected exit code {code}, got {ctx.result.exit_code}\nOutput:\n{ctx.result.output}"
    )


@then(parsers.parse('the output contains "{text}"'))
def _then_output_contains(ctx: SettingsContext, text: str):
    assert text in ctx.result.output, f"Expected {text!r} in output.\nActual output:\n{ctx.result.output}"


@then(parsers.parse('the settings file contains name "{name}" and planet "{planet}"'))
def _then_settings_file_contains_name_and_planet(ctx: SettingsContext, name: str, planet: str):
    settings_path = get_typerdrive_config().settings_path
    assert settings_path.exists(), f"Settings file not found at {settings_path}"
    data = json.loads(settings_path.read_text())
    assert data["name"] == name, f"Expected name {name!r}, got {data.get('name')!r}"
    assert data["planet"] == planet, f"Expected planet {planet!r}, got {data.get('planet')!r}"


@then(parsers.parse('the settings file contains name "{name}"'))
def _then_settings_file_contains_name(ctx: SettingsContext, name: str):
    settings_path = get_typerdrive_config().settings_path
    assert settings_path.exists(), f"Settings file not found at {settings_path}"
    data = json.loads(settings_path.read_text())
    assert data.get("name") == name, f"Expected name {name!r}, got {data.get('name')!r}"


@then(parsers.parse('the settings file has alignment "{alignment}"'))
def _then_settings_file_has_alignment(ctx: SettingsContext, alignment: str):
    settings_path = get_typerdrive_config().settings_path
    assert settings_path.exists()
    data = json.loads(settings_path.read_text())
    assert data.get("alignment") == alignment, f"Expected alignment {alignment!r}, got {data.get('alignment')!r}"


@then(parsers.parse('the settings file does not contain name "{name}"'))
def _then_settings_file_does_not_contain_name(ctx: SettingsContext, name: str):
    settings_path = get_typerdrive_config().settings_path
    if settings_path.exists():
        data = json.loads(settings_path.read_text())
        assert data.get("name") != name, f"Did not expect name {name!r} in settings file"


@then(parsers.parse('the settings file still contains name "{name}"'))
def _then_settings_file_still_contains_name(ctx: SettingsContext, name: str):
    settings_path = get_typerdrive_config().settings_path
    assert settings_path.exists()
    data = json.loads(settings_path.read_text())
    assert data.get("name") == name, f"Expected {name!r} still in settings file, got {data.get('name')!r}"
