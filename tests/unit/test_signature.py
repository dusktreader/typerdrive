"""
Tests for SignatureRewriter.
"""

from functools import wraps
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

        @wraps(func)
        def inner_wrapper(*args, **kwargs): ...

        inner_rewriter.apply(inner_wrapper)

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


class TestSignatureRewriterApply:
    def test_apply__sets_signature_on_wrapper(self):
        class Sentinel: ...

        def func(ctx: typer.Context, mgr: Sentinel) -> None: ...

        cloaked = Annotated[Sentinel | None, CloakingDevice]
        rewriter = SignatureRewriter(func)
        rewriter.cloak("mgr", cloaked)

        @wraps(func)
        def wrapper(ctx: typer.Context, *args, **kwargs): ...

        rewriter.apply(wrapper)

        sig = signature(wrapper)
        assert sig.parameters["mgr"].annotation == cloaked

    def test_apply__annotations_is_plain_dict(self):
        """__annotations__ must be a plain resolved dict, not a lazy __annotate__ closure."""
        def func(ctx: typer.Context, name: str) -> None: ...

        rewriter = SignatureRewriter(func)

        @wraps(func)
        def wrapper(ctx: typer.Context, *args, **kwargs): ...

        rewriter.apply(wrapper)

        assert isinstance(wrapper.__annotations__, dict)
        assert wrapper.__annotations__ == {"ctx": typer.Context, "name": str}

    def test_apply__annotations_reflects_overrides(self):
        class Sentinel: ...

        def func(ctx: typer.Context, mgr: Sentinel) -> None: ...

        cloaked = Annotated[Sentinel | None, CloakingDevice]
        rewriter = SignatureRewriter(func)
        rewriter.cloak("mgr", cloaked)

        @wraps(func)
        def wrapper(ctx: typer.Context, *args, **kwargs): ...

        rewriter.apply(wrapper)

        assert wrapper.__annotations__["mgr"] == cloaked
        assert wrapper.__annotations__["ctx"] is typer.Context

    def test_apply__neutralises_annotate_copied_by_wraps(self):
        """
        On Python 3.13+, functools.WRAPPER_ASSIGNMENTS includes __annotate__, so
        @wraps copies the original function's lazy __annotate__ onto the wrapper.
        apply() must neutralise it so Python 3.14 lazy evaluation never fires —
        either by deletion or by replacing it with one that returns the resolved dict.
        """
        def func(ctx: typer.Context, name: str) -> None: ...

        rewriter = SignatureRewriter(func)

        @wraps(func)
        def wrapper(ctx: typer.Context, *args, **kwargs): ...

        # On Python 3.13+, @wraps will have copied __annotate__ from func
        # Verify the precondition holds on this interpreter
        if not hasattr(wrapper, "__annotate__"):
            return  # pragma: no cover — older Python, nothing to test

        rewriter.apply(wrapper)

        # Either __annotate__ is gone, or it has been replaced with one that
        # returns the pre-resolved dict rather than the original lazy closure.
        if hasattr(wrapper, "__annotate__"):
            result = wrapper.__annotate__(1)  # type: ignore[attr-defined]  # ty: ignore[call-non-callable]
            assert result == {"ctx": typer.Context, "name": str}
        else:
            pass  # deleted — also fine
