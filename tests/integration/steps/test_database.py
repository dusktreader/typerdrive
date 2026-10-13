import asyncio
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import typer
from click.testing import Result
from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from typerdrive.config import get_typerdrive_config
from typerdrive.database.attach import attach_database
from typerdrive.database.commands import add_database_subcommand
from typerdrive.database.manager import DatabaseManager
from typerdrive.database.migrations import MigrationRegistry


@scenario("../features/database.feature", "Fresh attachment creates and migrates the database before the callback")
def test_fresh_attachment_initializes_database_before_callback():
    pass


@scenario("../features/database.feature", "Async commands persist rows across invocations")
def test_async_database_commands_persist_rows():
    pass


@scenario("../features/database.feature", "Sync wrappers persist rows across invocations")
def test_sync_database_commands_persist_rows():
    pass


@scenario("../features/database.feature", "Migrations run before callback and failures suppress the callback")
def test_migration_failure_suppresses_callback():
    pass


@scenario("../features/database.feature", "Empty migration descriptions suppress callbacks")
def test_empty_migration_description_suppresses_callback():
    pass


@scenario("../features/database.feature", "Empty migration SQL suppresses callbacks")
def test_empty_migration_sql_suppresses_callback():
    pass


@scenario("../features/database.feature", "Failed SQL migration rolls back and can be retried in registration order")
def test_failed_migration_rolls_back_and_retries_in_order():
    pass


@scenario("../features/database.feature", "Database path inspect and status do not create an absent database")
def test_database_commands_do_not_create_absent_file():
    pass


@scenario("../features/database.feature", "Reset rebuilds the current registered schema")
def test_database_reset_rebuilds_current_schema():
    pass


@scenario("../features/database.feature", "Setup creates an empty database and migrate applies pending schema")
def test_setup_and_migrate_workflow():
    pass


@scenario("../features/database.feature", "Declining reset preserves application data and migration history")
def test_declining_database_reset_preserves_rows():
    pass


@scenario("../features/database.feature", "Concurrent processes apply each migration exactly once")
def test_concurrent_process_migrations_apply_once():
    pass


@scenario("../features/database.feature", "Invoking an attached command from a running event loop fails clearly")
def test_active_loop_command_invocation_fails_clearly():
    pass


@scenario("../features/database.feature", "Async command failure closes the database manager")
def test_async_failure_closes_manager():
    pass


@scenario("../features/database.feature", "Cancellation closes the database manager")
def test_async_cancellation_closes_manager():
    pass


class DatabaseContext:
    cli: typer.Typer
    registry: MigrationRegistry
    result: Result
    results: list[Result]
    output: str
    database_path: Path
    entered: bool
    marker_directory: Path
    cancelled_manager: DatabaseManager | None
    failed_manager: DatabaseManager | None
    attachment_proof: bool
    setup_results: list[Result]
    pending_status: str
    migrate_absent: bool
    concurrent_process_results: list[tuple[str, str]]
    concurrent_process_codes: list[int | None]


@pytest.fixture
def ctx(tmp_home: Path, tmp_path: Path):
    context = DatabaseContext()
    context.database_path = get_typerdrive_config().database_path
    context.results = []
    context.output = ""
    context.entered = False
    context.marker_directory = tmp_path / "database-process"
    context.cancelled_manager = None
    context.failed_manager = None
    context.attachment_proof = False
    context.setup_results = []
    context.pending_status = ""
    context.migrate_absent = False
    yield context
    if context.marker_directory.exists():
        shutil.rmtree(context.marker_directory)


@given("a CLI app with database commands and migrations")
def _given_cli_with_database_commands(ctx: DatabaseContext):
    ctx.registry = MigrationRegistry()
    ctx.registry.register_migration("Create Item", "CREATE TABLE item (value TEXT);")
    ctx.cli = typer.Typer()
    add_database_subcommand(ctx.cli, ctx.registry)
    scenario_context = ctx

    @ctx.cli.command()
    @attach_database(ctx.registry)
    async def async_insert(ctx: typer.Context, database: DatabaseManager):
        assert scenario_context.database_path.exists()
        journal_mode = await database.fetch_value("PRAGMA journal_mode")
        table = await database.fetch_value("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'item'")
        assert journal_mode == "wal"
        assert table == "item"
        scenario_context.attachment_proof = True
        typer.echo("attachment ready: file exists, WAL active, migrated table item exists")
        assert ctx.obj.database_manager is database
        await database.execute("INSERT INTO item VALUES (?)", ("first row",))
        typer.echo("row inserted")

    @ctx.cli.command()
    @attach_database(ctx.registry)
    async def async_read(ctx: typer.Context, database: DatabaseManager):
        assert ctx.obj.database_manager is database
        rows = await database.fetch_all("SELECT value FROM item ORDER BY rowid")
        typer.echo(" ".join(row[0] for row in rows))

    @ctx.cli.command()
    @attach_database(ctx.registry)
    def sync_insert(ctx: typer.Context, database: DatabaseManager):
        assert ctx.obj.database_manager is database
        database.execute_sync("INSERT INTO item VALUES (?)", ("sync row",))
        typer.echo("row inserted")

    @ctx.cli.command()
    @attach_database(ctx.registry)
    def sync_read(ctx: typer.Context, database: DatabaseManager):
        assert ctx.obj.database_manager is database
        rows = database.fetch_all_sync("SELECT value FROM item ORDER BY rowid")
        typer.echo(" ".join(row[0] for row in rows))

    @ctx.cli.command()
    @attach_database(ctx.registry)
    def guarded(ctx: typer.Context):
        assert ctx.obj.database_manager is not None
        scenario_context.entered = True

    @ctx.cli.command()
    @attach_database(ctx.registry)
    async def fail(ctx: typer.Context, database: DatabaseManager):
        assert scenario_context.database_path.exists()
        journal_mode = await database.fetch_value("PRAGMA journal_mode")
        table = await database.fetch_value("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'item'")
        assert journal_mode == "wal"
        assert table == "item"
        scenario_context.failed_manager = database
        raise RuntimeError("command failed after attachment")

    @ctx.cli.command()
    @attach_database(ctx.registry)
    async def cancel(ctx: typer.Context, database: DatabaseManager):
        assert ctx.obj.database_manager is database
        scenario_context.cancelled_manager = database
        raise asyncio.CancelledError


@when(parsers.parse('an async command inserts "{value}"'))
def _when_async_insert(ctx: DatabaseContext, runner: CliRunner, value: str):
    assert value == "first row"
    assert not ctx.database_path.exists()
    ctx.result = runner.invoke(ctx.cli, ["async-insert"], prog_name="test")
    ctx.results.append(ctx.result)


@when("an async command reads the stored rows")
def _when_async_read(ctx: DatabaseContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["async-read"], prog_name="test")
    ctx.results.append(ctx.result)
    ctx.output += ctx.result.output


@when(parsers.parse('a sync command inserts "{value}"'))
def _when_sync_insert(ctx: DatabaseContext, runner: CliRunner, value: str):
    assert value == "sync row"
    ctx.result = runner.invoke(ctx.cli, ["sync-insert"], prog_name="test")
    ctx.results.append(ctx.result)


@when("a sync command reads the stored rows")
def _when_sync_read(ctx: DatabaseContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["sync-read"], prog_name="test")
    ctx.results.append(ctx.result)
    ctx.output += ctx.result.output


@given("a database with a migration checksum mismatch")
def _given_checksum_mismatch(ctx: DatabaseContext):
    async def seed() -> None:
        async with DatabaseManager(ctx.database_path) as manager:
            await ctx.registry.apply(manager)

    asyncio.run(seed())
    changed = MigrationRegistry()
    changed.register_migration("Create Item", "CREATE TABLE replacement (value TEXT);")
    ctx.registry._migrations[:] = changed.migrations


@given("a migration with an empty description")
def _given_empty_migration_description(ctx: DatabaseContext):
    invalid = MigrationRegistry()
    invalid.register_migration("", "CREATE TABLE item (value TEXT);")
    ctx.registry._migrations[:] = invalid.migrations


@given("a migration with empty SQL")
def _given_empty_migration_sql(ctx: DatabaseContext):
    invalid = MigrationRegistry()
    invalid.register_migration("Create Item", "  ")
    ctx.registry._migrations[:] = invalid.migrations


@given("a migration sequence with a failing second migration")
def _given_failing_second_migration(ctx: DatabaseContext):
    invalid = MigrationRegistry()
    invalid.register_migration("First Migration", "CREATE TABLE item (value TEXT);")
    invalid.register_migration("Second Migration", "CREATE TABLE extra_item (value TEXT); INVALID SQL;")
    ctx.registry._migrations[:] = invalid.migrations


@when("I invoke an attached command")
def _when_invoke_attached_command(ctx: DatabaseContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["guarded"], prog_name="test")


@when("I set up and migrate with failing SQL")
def _when_setup_and_migrate_failing_sql(ctx: DatabaseContext, runner: CliRunner):
    setup = runner.invoke(ctx.cli, ["db", "setup"], prog_name="test")
    assert setup.exit_code == 0, setup.output
    ctx.result = runner.invoke(ctx.cli, ["db", "migrate"], prog_name="test")


@when("I correct the second migration and migrate")
def _when_correct_second_migration(ctx: DatabaseContext, runner: CliRunner):
    corrected = MigrationRegistry()
    corrected.register_migration("First Migration", "CREATE TABLE item (value TEXT);")
    corrected.register_migration("Second Migration", "CREATE TABLE extra_item (value TEXT);")
    ctx.registry._migrations[:] = corrected.migrations
    ctx.result = runner.invoke(ctx.cli, ["db", "migrate"], prog_name="test")


@when("I run database path inspect and status")
def _when_database_read_commands(ctx: DatabaseContext, runner: CliRunner):
    for command in (["db", "path"], ["db", "inspect"], ["db", "status"]):
        result = runner.invoke(ctx.cli, command, prog_name="test")
        ctx.results.append(result)
        ctx.output += result.output
    ctx.result = ctx.results[-1]


@when("I run migrate against the absent database")
def _when_migrate_absent_database(ctx: DatabaseContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["db", "migrate"], prog_name="test")
    ctx.migrate_absent = not ctx.database_path.exists()


@when("I set up the database twice")
def _when_setup_database_twice(ctx: DatabaseContext, runner: CliRunner):
    for _ in range(2):
        result = runner.invoke(ctx.cli, ["db", "setup"], prog_name="test")
        ctx.setup_results.append(result)
        ctx.output += result.output
    pending = runner.invoke(ctx.cli, ["db", "status"], prog_name="test")
    ctx.results.append(pending)
    ctx.pending_status = pending.output


@when("I inspect, migrate, and check status")
def _when_inspect_migrate_and_check_status(ctx: DatabaseContext, runner: CliRunner):
    for command in (["db", "inspect"], ["db", "migrate"], ["db", "status"], ["db", "inspect"]):
        result = runner.invoke(ctx.cli, command, prog_name="test")
        ctx.results.append(result)
        ctx.output += result.output
    ctx.result = ctx.results[-1]


@when("I set up the database")
def _when_setup_database(ctx: DatabaseContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["db", "setup"], prog_name="test")


@given("the database contains an application row")
def _given_database_application_row(ctx: DatabaseContext, runner: CliRunner):
    seeded = runner.invoke(ctx.cli, ["async-insert"], prog_name="test")
    assert seeded.exit_code == 0, seeded.output


@when("I reset the database and confirm")
def _when_reset_confirmed(ctx: DatabaseContext, runner: CliRunner):
    changed = MigrationRegistry()
    changed.register_migration("Create Item", "CREATE TABLE replacement (value TEXT);")
    ctx.registry._migrations[:] = changed.migrations
    ctx.result = runner.invoke(ctx.cli, ["db", "reset"], input="y\n", prog_name="test")


@when("I decline database reset")
def _when_reset_declined(ctx: DatabaseContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["db", "reset"], input="n\n", prog_name="test")


@when("I invoke an attached command from an active event loop")
def _when_command_invoked_from_running_loop(ctx: DatabaseContext, runner: CliRunner):
    async def invoke() -> Result:
        return runner.invoke(ctx.cli, ["guarded"], prog_name="test")

    ctx.result = asyncio.run(invoke())


@when("an async command raises an error")
def _when_async_command_fails(ctx: DatabaseContext, runner: CliRunner):
    ctx.result = runner.invoke(ctx.cli, ["fail"], prog_name="test")


@when("an async command cancels itself")
def _when_cancel_async_command(ctx: DatabaseContext, runner: CliRunner):
    with pytest.raises(asyncio.CancelledError):
        runner.invoke(ctx.cli, ["cancel"], prog_name="test")


@when("two processes migrate the database at the same time")
def _when_two_processes_migrate(ctx: DatabaseContext, runner: CliRunner):
    setup = runner.invoke(ctx.cli, ["db", "setup"], prog_name="test")
    assert setup.exit_code == 0, setup.output
    ctx.marker_directory.mkdir()
    start = ctx.marker_directory / "start"
    ready_files = [ctx.marker_directory / f"ready-{index}" for index in range(2)]
    script = """
import asyncio
import sys
import time
from pathlib import Path
from typerdrive.database.manager import DatabaseManager
from typerdrive.database.migrations import MigrationRegistry

path, start, ready = sys.argv[1:]
Path(ready).touch()
while not Path(start).exists():
    time.sleep(0.01)
registry = MigrationRegistry()
registry.register_migration("Create Item", "CREATE TABLE item (value TEXT);")
async def migrate():
    async with DatabaseManager(path) as manager:
        await registry.apply(manager)
asyncio.run(migrate())
"""
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(ctx.database_path), str(start), str(ready)],
            cwd=Path(__file__).resolve().parents[3],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for ready in ready_files
    ]
    deadline = time.monotonic() + 20
    try:
        while not all(ready.exists() for ready in ready_files):
            assert all(process.poll() is None for process in processes)
            assert time.monotonic() < deadline
            time.sleep(0.01)
        start.touch()
        ctx.concurrent_process_results = [process.communicate(timeout=40) for process in processes]
        ctx.concurrent_process_codes = [process.returncode for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()


@then("the output proves attachment initialization completed")
def _then_attachment_initialization_is_proven(ctx: DatabaseContext):
    assert ctx.attachment_proof
    assert "file exists, WAL active, migrated table item exists" in ctx.result.output


@then("migrate fails without creating the database")
def _then_migrate_fails_without_creation(ctx: DatabaseContext):
    assert ctx.result.exit_code != 0
    assert ctx.migrate_absent
    assert not ctx.database_path.exists()


@then("setup succeeds and leaves application migrations pending")
def _then_setup_is_idempotent_and_pending(ctx: DatabaseContext):
    assert all(result.exit_code == 0 for result in ctx.setup_results)
    assert "already set up" in ctx.setup_results[1].output
    assert "pending 00000001create item" in ctx.pending_status


@then("the database has no application schema")
def _then_setup_has_no_application_schema(ctx: DatabaseContext):
    async def verify() -> tuple[str | None, str | None]:
        async with DatabaseManager(ctx.database_path) as manager:
            app_table = await manager.fetch_value(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'item'"
            )
            ledger = await manager.fetch_value(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = '_typerdrive_migrations'"
            )
            return app_table, ledger

    assert asyncio.run(verify()) == (None, None)


@then("migrations are applied and inspect reports WAL metadata")
def _then_migrations_and_inspection_succeed(ctx: DatabaseContext):
    assert all(result.exit_code == 0 for result in ctx.results)
    assert "applied 00000001create item" in ctx.output
    assert "Journal mode: wal" in ctx.output


@then("only the first migration is recorded")
def _then_failed_migration_rolls_back(ctx: DatabaseContext):
    async def verify() -> tuple[int, str | None, str | None]:
        async with DatabaseManager(ctx.database_path) as manager:
            count = await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations")
            item_table = await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'item'")
            extra_table = await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'extra_item'")
            return count, item_table, extra_table

    assert asyncio.run(verify()) == (1, "item", None), ctx.result.output


@then("migration ledger IDs match registration order")
def _then_migration_ids_match_registration_order(ctx: DatabaseContext):
    async def read_ids() -> list[str]:
        async with DatabaseManager(ctx.database_path) as manager:
            rows = await manager.fetch_all("SELECT migration_id FROM _typerdrive_migrations ORDER BY migration_index")
            return [row[0] for row in rows]

    assert ctx.result.exit_code == 0, ctx.result.output
    assert asyncio.run(read_ids()) == [migration.migration_id for migration in ctx.registry.migrations]


@then("failure handling closes the database manager")
def _then_failure_closes_manager(ctx: DatabaseContext):
    assert ctx.result.exit_code != 0
    assert ctx.failed_manager is not None
    assert not ctx.failed_manager.is_open


@then("both migration processes succeed")
def _then_both_migration_processes_succeed(ctx: DatabaseContext):
    assert ctx.concurrent_process_codes == [0, 0], ctx.concurrent_process_results


@then("the migration ledger and schema contain one application")
def _then_migration_was_applied_once(ctx: DatabaseContext):
    async def verify() -> tuple[int, int]:
        async with DatabaseManager(ctx.database_path) as manager:
            return (
                await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations"),
                await manager.fetch_value("SELECT COUNT(*) FROM item"),
            )

    assert asyncio.run(verify()) == (1, 0)


@then("the command succeeds")
def _then_command_succeeds(ctx: DatabaseContext):
    assert ctx.result.exit_code == 0, f"{ctx.result.exception}\n{ctx.result.output}"


@then("the command fails")
def _then_command_fails(ctx: DatabaseContext):
    assert ctx.result.exit_code != 0, ctx.result.output


@then("the output explains the event loop limitation")
def _then_event_loop_limitation_is_actionable(ctx: DatabaseContext):
    assert ctx.result.exception is not None
    assert "cannot run inside an event loop" in str(ctx.result.exception)
    assert not ctx.entered


@then("all database commands succeed")
def _then_all_database_commands_succeed(ctx: DatabaseContext):
    assert all(result.exit_code == 0 for result in ctx.results), [result.output for result in ctx.results]


@then(parsers.parse('the output contains "{value}"'))
def _then_output_contains(ctx: DatabaseContext, value: str):
    assert value in ctx.result.output + ctx.output


@then("the migration ledger contains 1 record")
def _then_one_migration_is_recorded(ctx: DatabaseContext):
    async def check() -> int:
        async with DatabaseManager(ctx.database_path) as manager:
            return await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations")

    assert asyncio.run(check()) == 1


@then("the application callback was not entered")
def _then_callback_not_entered(ctx: DatabaseContext):
    assert not ctx.entered


@then("the output reports the migration as pending")
def _then_pending_migration_reported(ctx: DatabaseContext):
    assert "pending 00000001create item" in ctx.output


@then("the database file remains absent")
def _then_database_file_absent(ctx: DatabaseContext):
    assert not ctx.database_path.exists()


@then("the reset database contains the current schema and no old row")
def _then_reset_schema_is_current(ctx: DatabaseContext):
    async def verify() -> tuple[str | None, str | None, list[tuple[str, str]]]:
        async with DatabaseManager(ctx.database_path) as manager:
            old_table = await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'item'")
            new_table = await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'replacement'")
            history = await manager.fetch_all(
                "SELECT migration_id, checksum FROM _typerdrive_migrations ORDER BY migration_index"
            )
            return old_table, new_table, [(row[0], row[1]) for row in history]

    old_table, new_table, history = asyncio.run(verify())
    current_migration = ctx.registry.migrations[0]
    assert old_table is None
    assert new_table == "replacement"
    assert history == [(current_migration.migration_id, current_migration.checksum)]


@then("the existing application row and migration history remain")
def _then_declined_reset_preserves_history(ctx: DatabaseContext):
    async def verify() -> tuple[str, str]:
        async with DatabaseManager(ctx.database_path) as manager:
            value = await manager.fetch_value("SELECT value FROM item")
            migration_id = await manager.fetch_value(
                "SELECT migration_id FROM _typerdrive_migrations WHERE migration_index = 1"
            )
            return value, migration_id

    assert asyncio.run(verify()) == ("first row", "00000001create item")


@then("cancellation closes the manager before it escapes")
def _then_cancellation_closes_manager(ctx: DatabaseContext):
    manager = ctx.cancelled_manager
    assert manager is not None
    assert not manager.is_open
