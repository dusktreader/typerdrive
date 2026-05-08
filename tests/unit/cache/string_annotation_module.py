# This module intentionally uses `from __future__ import annotations` so that
# all annotations are stored as strings rather than evaluated types.  This
# replicates the annotation-evaluation behaviour introduced in Python 3.14
# (PEP 649) and lets us test `attach_cache` against string annotations on
# any supported Python version.
from __future__ import annotations

import typer
from typerdrive.cache.attach import attach_cache, get_cache_manager
from typerdrive.cache.manager import CacheManager


def make_string_annotated_cli() -> typer.Typer:
    """
    Return a Typer app whose command function has string annotations.

    Because this module uses `from __future__ import annotations`, every type
    annotation in every function defined here is stored as a plain string in
    `__annotations__`.  Passing such a function to `attach_cache` previously
    caused a `NameError` because the decorator compared raw annotation strings
    against type objects using `is`.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_cache()
    def noop(ctx: typer.Context) -> None:
        manager = get_cache_manager(ctx)
        assert isinstance(manager, CacheManager)
        print("Passed!")

    return cli


def make_string_annotated_manager_cli() -> typer.Typer:
    """
    Return a Typer app whose command uses a `CacheManager` parameter with string annotations.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_cache()
    def noop(ctx: typer.Context, mgr: CacheManager) -> None:
        assert isinstance(mgr, CacheManager)
        print("Passed!")

    return cli
