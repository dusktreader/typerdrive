"""
Provide a helper class for rewriting function signatures in decorator contexts.
"""

from collections.abc import Callable
from inspect import Parameter, Signature, signature
from typing import Any, get_type_hints


class SignatureRewriter:
    """
    Collects annotation overrides for specific parameters and builds a new
    `Signature` with those overrides applied.

    Typical use: inside a decorator, call `cloak()` for each parameter whose
    annotation should be replaced, then assign `wrapper.__signature__ = rewriter.build()`
    after the wrapper function is defined.
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
