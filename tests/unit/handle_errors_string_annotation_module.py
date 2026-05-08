# This module intentionally uses `from __future__ import annotations` so that
# all annotations are stored as strings rather than evaluated types.  This
# replicates the annotation-evaluation behaviour introduced in Python 3.14
# (PEP 649) and lets us test `handle_errors` against string annotations on
# any supported Python version.
from __future__ import annotations

import typer
from typerdrive.exceptions import TyperdriveError
from typerdrive.handle_errors import handle_errors


class SomeError(TyperdriveError):
    pass


def make_string_annotated_cli() -> typer.Typer:
    """
    Return a Typer app whose command function has string annotations.

    Because this module uses `from __future__ import annotations`, every type
    annotation in every function defined here is stored as a plain string in
    `__annotations__`.  Passing such a function to `handle_errors` previously
    caused a `NameError` when Python 3.14's lazy annotation machinery tried to
    resolve types in the wrong scope.
    """
    cli = typer.Typer()

    @cli.command()
    @handle_errors("Something went wrong")
    def noop(name: str = "jawa") -> None:
        print(f"Hello, {name}!")

    return cli


def make_string_annotated_with_context_cli() -> typer.Typer:
    """
    Return a Typer app whose command uses a `typer.Context` parameter with string annotations.
    """
    cli = typer.Typer()

    @cli.command()
    @handle_errors("Something went wrong")
    def noop(ctx: typer.Context, name: str = "jawa") -> None:
        print(f"Hello, {name}!")

    return cli
