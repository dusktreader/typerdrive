"""
Provide functions for parsing pydantic models.

These are intended to be used with `typer-repyt` dynamic command function builder where arguments or options will be
provided as JSON strings that need to be deserialized into pydantic model instances.
"""

import json
from collections.abc import Callable
from functools import partial
from typing import Any

from pydantic import BaseModel


def _validating_parser(model_type: type[BaseModel], val: str) -> dict[str, Any]:
    """
    Provide a parser that converts a string into a dict after validating the values.

    This is needed for the settings commands to be able to use nested pydantic models.
    Note that it _does not_ return an instance of the model. This is because it is simplest to let the model be
    constructed from a plain dictionary.
    """
    model_type.model_validate_json(val)
    return json.loads(val)


def make_parser(model_type: type[BaseModel]) -> Callable[[str], dict[str, Any]]:
    """
    Construct a partial that wraps `model_parser` and gives it a `__name__`.

    This is needed because `typer_repyt` requires the callable to have a `__name__` attribute to bind it to the
    namespace of a dynamically generated command function.
    """
    parser = partial(_validating_parser, model_type)

    # This works fine, but pyright/basedpyright does not like it!
    parser.__name__ = f"parse_{model_type.__name__}"  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

    return parser
