# This module intentionally uses `from __future__ import annotations` so that
# all annotations are stored as strings rather than evaluated types.  This
# replicates the annotation-evaluation behaviour introduced in Python 3.14
# (PEP 649) and lets us test `attach_logging` against string annotations on
# any supported Python version.
from __future__ import annotations

import typer
from typerdrive.logging.attach import attach_logging, get_logging_manager
from typerdrive.logging.manager import LoggingManager


def make_string_annotated_cli() -> typer.Typer:
    """
    Return a Typer app whose command function has string annotations.

    Because this module uses `from __future__ import annotations`, every type
    annotation in every function defined here is stored as a plain string in
    `__annotations__`.  Passing such a function to `attach_logging` previously
    caused a `NameError` because the decorator compared raw annotation strings
    against type objects using `is`.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_logging()
    def noop(ctx: typer.Context) -> None:
        manager = get_logging_manager(ctx)
        assert isinstance(manager, LoggingManager)
        print("Passed!")

    return cli


def make_string_annotated_manager_cli() -> typer.Typer:
    """
    Return a Typer app whose command uses a `LoggingManager` parameter with string annotations.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_logging()
    def noop(ctx: typer.Context, mgr: LoggingManager) -> None:
        assert isinstance(mgr, LoggingManager)
        print("Passed!")

    return cli
