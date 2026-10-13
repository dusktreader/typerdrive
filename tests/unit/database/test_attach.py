import asyncio
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import click
import pytest
import typer
from typer.testing import CliRunner
from typerdrive.database.attach import attach_database, get_database_manager
from typerdrive.database.exceptions import DatabaseLifecycleError
from typerdrive.database.manager import DatabaseManager
from typerdrive.database.migrations import MigrationRegistry
from typerdrive.handle_errors import handle_errors


class TestAttachDatabase:
    def test_sync_command_injects_manager_and_context_lookup(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (value TEXT);")
        cli = typer.Typer()
        results = []

        @cli.command()
        @attach_database(registry)
        def command(ctx: typer.Context, database: DatabaseManager):
            assert database is get_database_manager(ctx)
            database.execute_sync("INSERT INTO item VALUES (?)", ("ok",))
            results.append(database.fetch_value_sync("SELECT value FROM item"))

        result = CliRunner().invoke(cli, [])
        assert result.exit_code == 0, result.output
        assert results == ["ok"]

    def test_async_command_is_awaited_and_database_stays_open(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        registry = MigrationRegistry()
        registry.register_migration("Create Item", "CREATE TABLE item (value TEXT);")
        cli = typer.Typer()
        output = []

        @cli.command()
        @attach_database(registry)
        async def command(ctx: typer.Context, database: DatabaseManager):
            await asyncio.sleep(0)
            await database.execute("INSERT INTO item VALUES ('done')")
            output.append(await database.fetch_value("SELECT value FROM item"))

        result = CliRunner().invoke(cli, [])
        assert result.exit_code == 0, result.output
        assert output == ["done"]

    def test_migration_failure_prevents_command_body(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        registry = MigrationRegistry()
        registry.register_migration("Broken", "INVALID SQL;")
        cli = typer.Typer()
        entered = []

        @cli.command()
        @attach_database(registry)
        def command(ctx: typer.Context):
            entered.append(True)

        result = CliRunner().invoke(cli, [])
        assert result.exit_code != 0
        assert entered == []

    def test_async_boundary_rejects_running_loop(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        cli = typer.Typer()

        @cli.command()
        @attach_database()
        async def command(ctx: typer.Context):
            await asyncio.sleep(0)

        async def scenario():
            result = CliRunner().invoke(cli, [])
            assert result.exit_code != 0
            assert isinstance(result.exception, DatabaseLifecycleError)
            assert "inside an event loop" in str(result.exception)

        asyncio.run(scenario())

    def test_manager_is_closed_when_async_callback_fails(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        cli = typer.Typer()
        managers = []

        @cli.command()
        @attach_database()
        async def command(ctx: typer.Context, database: DatabaseManager):
            managers.append(database)
            await asyncio.sleep(0)
            raise ValueError("callback failed")

        result = CliRunner().invoke(cli, [])
        assert result.exit_code != 0
        assert managers and not managers[0].is_open

    def test_cancelled_async_command_closes_manager(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        cli = typer.Typer()
        managers = []

        @cli.command()
        @attach_database()
        async def command(ctx: typer.Context, database: DatabaseManager):
            managers.append(database)
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            CliRunner().invoke(cli, [])
        assert managers and not managers[0].is_open

    def test_context_lookup_rejects_missing_database(self):
        ctx = typer.Context(click.Command("test"))
        try:
            get_database_manager(ctx)
        except Exception as error:
            assert "attach_database" in str(error)
        else:
            raise AssertionError("Missing manager did not fail")

    def test_handle_errors_handles_async_exception_after_await_in_both_orders(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        cli = typer.Typer()

        @cli.command("attach-first")
        @attach_database()
        @handle_errors("Async command failed")
        async def attach_first(ctx: typer.Context):
            await asyncio.sleep(0)
            raise DatabaseLifecycleError("failure after await")

        @cli.command("errors-first")
        @handle_errors("Async command failed")
        @attach_database()
        async def errors_first(ctx: typer.Context):
            await asyncio.sleep(0)
            raise DatabaseLifecycleError("failure after await")

        runner = CliRunner()
        for command_name in ("attach-first", "errors-first"):
            result = runner.invoke(cli, [command_name])
            assert result.exit_code == 1
            assert "failure after await" in result.output

    def test_sync_callable_returning_coroutine_is_awaited_and_finalized(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        cli = typer.Typer()
        finalized = []

        @cli.command()
        @attach_database()
        @handle_errors("Async command failed", do_finally=lambda: finalized.append(True))
        def command(ctx: typer.Context):
            async def work():
                await asyncio.sleep(0)
                raise DatabaseLifecycleError("failure after await")

            return work()

        result = CliRunner().invoke(cli, [])
        assert result.exit_code == 1
        assert "failure after await" in result.output
        assert finalized == [True]

    def test_sync_callable_awaitable_preserves_context_through_adapter(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        context_value = ContextVar("attached_context_value", default="missing")
        context_value.set("caller context")
        cli = typer.Typer()
        results = []

        @cli.command()
        @attach_database()
        def command(ctx: typer.Context):
            async def work():
                await asyncio.sleep(0)
                results.append(context_value.get())

            return work()

        result = CliRunner().invoke(cli, [])
        assert result.exit_code == 0, result.output
        assert results == ["caller context"]

    def test_manager_injection_preserves_string_annotations(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        namespace: dict[str, Any] = {
            "typer": typer,
            "DatabaseManager": DatabaseManager,
            "attach_database": attach_database,
        }
        exec(
            "def command(ctx: 'typer.Context', database: 'DatabaseManager'):\n"
            "    database.execute_sync('SELECT 1')\n"
            "command = attach_database()(command)\n",
            namespace,
        )
        cli = typer.Typer()
        cli.command()(namespace["command"])
        result = CliRunner().invoke(cli, [])
        assert result.exit_code == 0, result.output
