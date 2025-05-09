import typer

from typerdrive.exceptions import handle_errors
from typerdrive.logging.attach import attach_logging
from typerdrive.logging.exceptions import LoggingError
from typerdrive.logging.manager import LoggingManager


@handle_errors("Failed to show log", handle_exc_class=LoggingError)
@attach_logging()
def show(ctx: typer.Context, manager: LoggingManager):  # pyright: ignore[reportUnusedParameter]
    manager.show()


def add_show(cli: typer.Typer):
    cli.command()(show)


@handle_errors("Failed to audit log dir", handle_exc_class=LoggingError)
@attach_logging()
def audit(ctx: typer.Context, manager: LoggingManager):  # pyright: ignore[reportUnusedParameter]
    manager.audit()


def add_audit(cli: typer.Typer):
    cli.command()(audit)


@handle_errors("Failed to clear log dir", handle_exc_class=LoggingError)
@attach_logging()
def clear(ctx: typer.Context, manager: LoggingManager):  # pyright: ignore[reportUnusedParameter]
    typer.confirm("Are you sure you want to clear all log files from the log directory?", abort=True)
    manager.clear()


def add_clear(cli: typer.Typer):
    cli.command()(clear)


def add_logs_subcommand(cli: typer.Typer):
    logs_cli = typer.Typer(help="Manage logs for the app")

    for cmd in [add_clear, add_show, add_audit]:
        cmd(logs_cli)

    cli.add_typer(logs_cli, name="logs")
