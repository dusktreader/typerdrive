"""
Step definitions for the cache BDD feature.

Each scenario drives a real typer.Typer() app assembled inline with
the typerdrive cache decorators/commands, then invokes it through
typer's CliRunner.
"""

import pytest
import typer
from click.testing import Result
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from typerdrive.cache.commands import add_cache_subcommand
from typerdrive.cache.manager import CacheManager


# ---------------------------------------------------------------------------
# Scenario bindings
# ---------------------------------------------------------------------------


@scenario("../features/cache.feature", "Show displays all cache entries")
def test_show_displays_all_cache_entries():
    pass


@scenario("../features/cache.feature", "Show with stats flag displays cache statistics")
def test_show_with_stats_flag():
    pass


@scenario("../features/cache.feature", "Clear removes all entries after confirmation")
def test_clear_removes_all_entries():
    pass


@scenario("../features/cache.feature", "Clear is cancelled when confirmation is denied")
def test_clear_is_cancelled():
    pass


@scenario("../features/cache.feature", "Clear removes only entries with a specific group")
def test_clear_removes_entries_with_group():
    pass


# ---------------------------------------------------------------------------
# Shared state container
# ---------------------------------------------------------------------------


class CacheContext:
    cli: typer.Typer
    result: Result


@pytest.fixture
def ctx() -> CacheContext:
    return CacheContext()


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("a CLI app with cache subcommand")
def _given_cli_with_cache_subcommand(ctx: CacheContext):
    ctx.cli = typer.Typer()
    add_cache_subcommand(ctx.cli)


@given(parsers.parse('the cache contains key "{key}" with value "{value}"'))
def _given_cache_contains_key_value(key: str, value: str):
    manager = CacheManager()
    manager.set(key, value)


@given(parsers.parse('the cache contains key "{key}" with value "{value}" in group "{group}"'))
def _given_cache_contains_key_value_group(key: str, value: str, group: str):
    manager = CacheManager()
    manager.set(key, value, group=group)


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("I run the cache show command")
def _when_cache_show(ctx: CacheContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["cache", "show"], prog_name="test")


@when(parsers.parse('I run the cache show command with "{flag}"'))
def _when_cache_show_with_flag(ctx: CacheContext, runner: CliRunner, flag: str):
    ctx.result = runner.invoke(ctx.cli, ["cache", "show", flag], prog_name="test")


@when(parsers.parse('I run the cache clear command and confirm with "{answer}"'))
def _when_cache_clear_with_confirmation(ctx: CacheContext, runner: CliRunner, answer: str):
    ctx.result = runner.invoke(ctx.cli, ["cache", "clear"], input=answer, prog_name="test")


@when(parsers.parse('I run the cache clear command with "{flag}" and confirm with "{answer}"'))
def _when_cache_clear_with_flag_and_confirmation(ctx: CacheContext, runner: CliRunner, flag: str, answer: str):
    ctx.result = runner.invoke(ctx.cli, ["cache", "clear", flag], input=answer, prog_name="test")


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the command succeeds")
def _then_command_succeeds(ctx: CacheContext):
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}\n"
        f"Exception: {ctx.result.exception}\n"
        f"Output:\n{ctx.result.output}"
    )


@then(parsers.parse("the command fails with exit code {code:d}"))
def _then_command_fails(ctx: CacheContext, code: int):
    assert ctx.result.exit_code == code, (
        f"Expected exit code {code}, got {ctx.result.exit_code}\nOutput:\n{ctx.result.output}"
    )


@then(parsers.parse('the output contains "{text}"'))
def _then_output_contains(ctx: CacheContext, text: str):
    assert text in ctx.result.output, f"Expected {text!r} in output.\nActual output:\n{ctx.result.output}"


@then("the cache is empty")
def _then_cache_is_empty():
    manager = CacheManager()
    assert len(manager.keys()) == 0, f"Expected cache to be empty, but found keys: {manager.keys()}"


@then(parsers.parse('the cache still contains key "{key}"'))
def _then_cache_still_contains_key(key: str):
    manager = CacheManager()
    assert manager.get(key) is not None, f"Expected key {key!r} to still be in cache"


@then(parsers.parse('the cache does not contain key "{key}"'))
def _then_cache_does_not_contain_key(key: str):
    manager = CacheManager()
    assert manager.get(key) is None, f"Expected key {key!r} to not be in cache"
