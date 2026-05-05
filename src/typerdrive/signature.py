"""
Provide a helper class for rewriting function signatures in decorator contexts.
"""

from collections.abc import Callable
from inspect import Parameter, Signature, signature
from typing import Any, get_type_hints


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
        Stamp the rewritten `Signature` onto the wrapper function.

        Sets `__signature__` so introspection tools see the rewritten parameters,
        then replaces `__annotations__` with an eagerly-evaluated dict that matches
        the rewritten signature exactly.

        On Python 3.14+, `inspect.signature()` on a plain function bypasses
        `__signature__` and calls `get_annotations()`, which triggers the lazy
        `__annotate__` closure — which references names (e.g. `Context`) that are
        not in scope at evaluation time. Replacing `__annotations__` with a plain
        pre-resolved dict prevents that evaluation entirely.
        """
        sig = self.build()
        setattr(wrapper, "__signature__", sig)
        wrapper.__annotations__ = {
            name: p.annotation
            for name, p in sig.parameters.items()
            if p.annotation is not p.empty
        }
