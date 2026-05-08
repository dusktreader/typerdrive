"""
Provide a helper class for rewriting function signatures in decorator contexts.
"""

from collections.abc import Callable
from functools import update_wrapper
from inspect import Parameter, Signature, signature
from typing import Any, get_type_hints

METADATA_ASSIGNMENTS = ["__module__", "__name__", "__qualname__", "__doc__"]


class SignatureRewriter:
    """
    Collects annotation overrides for specific parameters and builds a new
    `Signature` with those overrides applied, then stamps it onto a wrapper.

    Typical use: inside a decorator, call `cloak()` for each parameter whose
    annotation should be replaced, then call `apply(wrapper)` after the wrapper
    function is defined.
    """

    func: Callable
    overrides: dict[str, Any]
    hints: dict[str, Any]
    sig: Signature

    def __init__(self, func: Callable) -> None:
        self.func = func
        self.overrides = {}
        self.hints = get_type_hints(func, include_extras=True)
        self.sig = signature(func)

    def cloak(self, name: str, annotation: Any) -> None:
        """
        Register an annotation override for the parameter with the given name.
        """
        self.overrides[name] = annotation

    def build(self) -> Signature:
        """
        Return a new `Signature` with registered overrides applied.
        Parameters with no override retain their existing annotation.
        """
        new_params: list[Parameter] = [
            p.replace(annotation=self.overrides.get(p.name, p.annotation))
            for p in self.sig.parameters.values()
        ]
        return self.sig.replace(parameters=new_params)

    def apply(self, wrapper: Callable) -> None:
        """
        Copy identity metadata from the original function onto the wrapper, then
        stamp the rewritten `Signature` onto it.

        Uses `update_wrapper` with only `METADATA_ASSIGNMENTS` so that
        `__annotate__`, `__annotations__`, and `__wrapped__` are never copied from
        the original function — those are what trigger Python 3.14's lazy annotation
        evaluation in the wrong scope.

        Then sets `__signature__` and replaces `__annotations__` with a pre-resolved
        dict. Also deletes `__annotate__` if present as a safety net for callers that
        may have set it via other means.
        """
        update_wrapper(wrapper, self.func, assigned=METADATA_ASSIGNMENTS, updated=[])
        # update_wrapper always sets __wrapped__ regardless of `assigned`; remove it
        # so inspect.signature() with eval_str=True (as typer uses) does not follow
        # the chain back to the original function and trigger its lazy __annotate__.
        try:
            del wrapper.__wrapped__  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        except AttributeError:
            pass
        sig = self.build()
        setattr(wrapper, "__signature__", sig)
        resolved = {
            name: p.annotation
            for name, p in sig.parameters.items()
            if p.annotation is not p.empty
        }
        wrapper.__annotations__ = resolved
        # Replace __annotate__ (copied by update_wrapper on Python 3.13+) with a
        # callable that returns the pre-resolved dict. On Python 3.14 it cannot be
        # deleted (it's a slot), so we overwrite it instead.
        if hasattr(wrapper, "__annotate__"):
            try:
                wrapper.__annotate__ = lambda format: resolved  # type: ignore[attr-defined]  # ty: ignore[invalid-assignment]
            except (AttributeError, TypeError):
                pass
