# This module intentionally uses `from __future__ import annotations` so that
# all annotations are stored as strings rather than evaluated types.  This
# replicates the annotation-evaluation behaviour introduced in Python 3.14
# (PEP 649) and lets us test `attach_files` against string annotations on
# any supported Python version.
from __future__ import annotations

import typer
from typerdrive.files.attach import attach_files, get_files_manager
from typerdrive.files.manager import FilesManager


def make_string_annotated_cli() -> typer.Typer:
    """
    Return a Typer app whose command function has string annotations.

    Because this module uses `from __future__ import annotations`, every type
    annotation in every function defined here is stored as a plain string in
    `__annotations__`.  Passing such a function to `attach_files` previously
    caused a `NameError` because the decorator compared raw annotation strings
    against type objects using `is`.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_files()
    def noop(ctx: typer.Context) -> None:
        manager = get_files_manager(ctx)
        assert isinstance(manager, FilesManager)
        print("Passed!")

    return cli


def make_string_annotated_manager_cli() -> typer.Typer:
    """
    Return a Typer app whose command uses a `FilesManager` parameter with string annotations.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_files()
    def noop(ctx: typer.Context, mgr: FilesManager) -> None:
        assert isinstance(mgr, FilesManager)
        print("Passed!")

    return cli
