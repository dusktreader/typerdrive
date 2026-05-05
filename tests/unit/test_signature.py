"""
Tests for SignatureRewriter.
"""

from inspect import signature
from typing import Annotated

import typer

from typerdrive.cloaked import CloakingDevice
from typerdrive.signature import SignatureRewriter


class TestSignatureRewriter:
    def test_build__preserves_all_parameters_when_no_overrides(self):
        def func(ctx: typer.Context, name: str, count: int = 0) -> None: ...

        rewriter = SignatureRewriter(func)
        result = rewriter.build()

        assert list(result.parameters.keys()) == ["ctx", "name", "count"]
        assert result.parameters["ctx"].annotation is typer.Context
        assert result.parameters["name"].annotation is str
        assert result.parameters["count"].annotation is int

    def test_build__applies_single_override(self):
        class Sentinel: ...

        def func(ctx: typer.Context, mgr: Sentinel) -> None: ...

        cloaked = Annotated[Sentinel | None, CloakingDevice]
        rewriter = SignatureRewriter(func)
        rewriter.cloak("mgr", cloaked)
        result = rewriter.build()

        assert result.parameters["ctx"].annotation is typer.Context
        assert result.parameters["mgr"].annotation == cloaked

    def test_build__applies_multiple_overrides(self):
        class Foo: ...
        class Bar: ...

        def func(ctx: typer.Context, foo: Foo, bar: Bar, name: str) -> None: ...

        cloaked_foo = Annotated[Foo | None, CloakingDevice]
        cloaked_bar = Annotated[Bar | None, CloakingDevice]
        rewriter = SignatureRewriter(func)
        rewriter.cloak("foo", cloaked_foo)
        rewriter.cloak("bar", cloaked_bar)
        result = rewriter.build()

        assert result.parameters["foo"].annotation == cloaked_foo
        assert result.parameters["bar"].annotation == cloaked_bar
        assert result.parameters["name"].annotation is str

    def test_build__preserves_existing_annotated_metadata(self):
        opt = typer.Option(help="A group")

        def func(
            ctx: typer.Context,
            group: Annotated[str | None, opt] = None,
        ) -> None: ...

        rewriter = SignatureRewriter(func)
        result = rewriter.build()

        ann = result.parameters["group"].annotation
        from typing import get_args
        assert get_args(ann)[1] is opt

    def test_build__does_not_mutate_original_signature(self):
        class Sentinel: ...

        def func(ctx: typer.Context, mgr: Sentinel) -> None: ...

        orig_sig = signature(func)
        rewriter = SignatureRewriter(func)
        rewriter.cloak("mgr", Annotated[Sentinel | None, CloakingDevice])
        rewriter.build()

        assert signature(func) == orig_sig

    def test_build__preserves_annotation_from_inner_decorator(self):
        """
        When decorators are stacked, the outer decorator's SignatureRewriter
        should not overwrite annotations already cloaked by an inner decorator.
        """
        class Inner: ...
        class Outer: ...

        cloaked_inner = Annotated[Inner | None, CloakingDevice]

        def func(ctx: typer.Context, inner: Inner, outer: Outer) -> None: ...

        # Simulate inner decorator having already rewritten the signature
        inner_rewriter = SignatureRewriter(func)
        inner_rewriter.cloak("inner", cloaked_inner)

        from functools import wraps

        @wraps(func)
        def inner_wrapper(*args, **kwargs): ...

        inner_wrapper.__signature__ = inner_rewriter.build()  # type: ignore[attr-defined]

        # Outer decorator wraps the inner wrapper, only cloaks 'outer'
        cloaked_outer = Annotated[Outer | None, CloakingDevice]
        outer_rewriter = SignatureRewriter(inner_wrapper)
        outer_rewriter.cloak("outer", cloaked_outer)
        result = outer_rewriter.build()

        assert result.parameters["inner"].annotation == cloaked_inner
        assert result.parameters["outer"].annotation == cloaked_outer

    def test_hints__resolves_annotated_extras(self):
        opt = typer.Option(help="A thing")

        def func(name: Annotated[str, opt]) -> None: ...

        rewriter = SignatureRewriter(func)
        assert rewriter.hints["name"] == Annotated[str, opt]
