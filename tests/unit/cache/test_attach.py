from pathlib import Path

import typer
from typerdrive.cache.attach import attach_cache, get_cache_manager
from typerdrive.cache.exceptions import CacheError
from typerdrive.cache.manager import CacheManager

from tests.unit.cache.string_annotation_module import (
    make_string_annotated_cli,
    make_string_annotated_manager_cli,
)
from tests.unit.helpers import check_output, match_output


class TestAttachCache:
    def test_attach_cache__adds_cache_manager_to_context(self):
        cli: typer.Typer = typer.Typer()

        @cli.command()
        @attach_cache()
        def noop(ctx: typer.Context):
            manager = ctx.obj.cache_manager
            assert isinstance(manager, CacheManager)

        check_output(cli, prog_name="test")

    def test_attach_cache__show(self, fake_cache_path: Path):
        cli = typer.Typer()

        @cli.command()
        @attach_cache(show=True)
        def noop(ctx: typer.Context):
            manager = get_cache_manager(ctx)
            manager.set("jawa", b"jawa")
            manager.set("ewok", b"ewok")
            manager.set("hutt/pyke", b"hutt & pyke")

        expected_pattern = [
            "Cache contains 3 entries",
            "Key",
            "Group",
            "ewok",
            "hutt/pyke",
            "jawa",
        ]
        match_output(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )


class TestWithParameters:
    def test_attach_cache__with_manager_parameter(self, fake_cache_path: Path):
        cli = typer.Typer()

        @cli.command()
        @attach_cache(show=True)
        def noop(ctx: typer.Context, mgr: CacheManager):
            mgr.set("jawa", b"jawa")
            mgr.set("ewok", b"ewok")
            mgr.set("hutt/pyke", b"hutt & pyke")

        expected_pattern = [
            "Cache contains 3 entries",
            "Key",
            "Group",
            "ewok",
            "hutt/pyke",
            "jawa",
        ]
        match_output(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )


class TestGetManager:
    def test_get_cache_manager__extracts_cache_manager_from_context(self, fake_cache_path: Path):
        cli = typer.Typer()

        @cli.command()
        @attach_cache()
        def noop(ctx: typer.Context):
            manager = get_cache_manager(ctx)
            assert isinstance(manager, CacheManager)
            assert manager.cache_dir == fake_cache_path
            print("Passed!")

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )

    def test_get_cache_manager__raises_exception_if_context_has_no_manager(self):
        cli = typer.Typer()

        @cli.command()
        def noop(ctx: typer.Context):
            get_cache_manager(ctx)
            print("Passed!")

        match_output(
            cli,
            exception_type=CacheError,
            exception_pattern="Cache is not bound to the context",
            exit_code=1,
            prog_name="test",
        )

    def test_get_cache_manager__raises_exception_if_non_manager_retrieved(self):
        cli = typer.Typer()

        @cli.command()
        @attach_cache()
        def noop(ctx: typer.Context):
            ctx.obj.cache_manager = "Not a manager!"
            get_cache_manager(ctx)
            print("Passed!")

        match_output(
            cli,
            exception_type=CacheError,
            exception_pattern="Item in user context at `cache_manager` was not a CacheManager",
            exit_code=1,
            prog_name="test",
        )


class TestStringAnnotations:
    """
    Verify that `attach_cache` works correctly when the decorated function
    stores its annotations as strings rather than resolved types.

    This happens in any module that uses `from __future__ import annotations`
    (all Python versions) and is the default behaviour in Python 3.14+ (PEP 649).
    Previously, the decorator compared raw `__annotations__` values against type
    objects using `is`, which always failed for string annotations and could raise
    a `NameError` when Python's machinery tried to resolve the strings.
    """

    def test_cache_attached_with_string_annotations(self, fake_cache_path: Path):
        """Cache manager is attached correctly when annotations are strings."""
        cli = make_string_annotated_cli()

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )

    def test_manager_parameter_injected_with_string_annotations(self, fake_cache_path: Path):
        """CacheManager parameter is injected correctly when annotations are strings."""
        cli = make_string_annotated_manager_cli()

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )
