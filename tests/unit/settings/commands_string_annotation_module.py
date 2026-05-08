# This module intentionally uses `from __future__ import annotations` so that
# all annotations are stored as strings rather than evaluated types.  This
# replicates the annotation-evaluation behaviour introduced in Python 3.14
# (PEP 649) and lets us test `settings/commands.py` against string annotations
# on any supported Python version.
#
# The `build_command` path is particularly important: it dynamically constructs
# command functions and applies decorators (including `attach_settings`) in the
# `settings/commands.py` module scope.  Python 3.14's lazy `__annotate__` must
# be able to resolve `Context` and `Annotated` in that scope, which is why
# `settings/commands.py` explicitly re-exports those names.
from __future__ import annotations

import typer
from typerdrive.settings.commands import add_bind, add_reset, add_show, add_unset, add_update

from tests.unit.settings.models import DefaultSettingsModel


def make_string_annotated_bind_cli() -> typer.Typer:
    """
    Return a Typer app with the `bind` command built via `add_bind`.

    The annotations in this module are strings (due to `from __future__ import
    annotations`), but the functions produced by `build_command` inside
    `settings/commands.py` live in that module's own scope where `Context` and
    `Annotated` are resolvable.  If those names were absent from that scope the
    test would fail with a `NameError`.
    """
    cli = typer.Typer()
    add_bind(cli, DefaultSettingsModel)
    return cli


def make_string_annotated_update_cli() -> typer.Typer:
    """Return a Typer app with the `update` command built via `add_update`."""
    cli = typer.Typer()
    add_update(cli, DefaultSettingsModel)
    return cli


def make_string_annotated_unset_cli() -> typer.Typer:
    """Return a Typer app with the `unset` command built via `add_unset`."""
    cli = typer.Typer()
    add_unset(cli, DefaultSettingsModel)
    return cli


def make_string_annotated_show_cli() -> typer.Typer:
    """Return a Typer app with the `show` command built via `add_show`."""
    cli = typer.Typer()
    add_show(cli, DefaultSettingsModel)
    return cli


def make_string_annotated_reset_cli() -> typer.Typer:
    """Return a Typer app with the `reset` command built via `add_reset`."""
    cli = typer.Typer()
    add_reset(cli, DefaultSettingsModel)
    return cli
