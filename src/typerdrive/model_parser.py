"""
Provide functions for parsing pydantic models.

These are intended to be used with `typer-repyt` dynamic command function builder where arguments or options will be
provided as JSON strings that need to be deserialized into pydantic model instances.
"""

import json
import re
from collections.abc import Callable
from functools import partial
from typing import Any, get_args, get_origin

from pydantic import BaseModel, TypeAdapter

_SUPPORTED_COLLECTIONS = (list, set, frozenset, tuple, dict)


def is_model_type(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def is_model_collection(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin not in _SUPPORTED_COLLECTIONS:
        return False
    args = get_args(annotation)
    value_args = args[1:] if origin is dict else args
    return any(is_model_type(arg) or is_model_collection(arg) for arg in value_args)


def validating_parser(annotation: Any, val: str) -> Any:
    """
    Validate JSON input for a model or supported collection of models.

    Return plain Python data so the settings model can construct the model instances.
    """
    TypeAdapter(annotation).validate_json(val)
    return json.loads(val)


def make_parser(annotation: Any) -> Callable[[str], Any]:
    """
    Construct a partial that wraps `model_parser` and gives it a `__name__`.

    This is needed because `typer_repyt` requires the callable to have a `__name__` attribute to bind it to the
    namespace of a dynamically generated command function.
    """
    parser = partial(validating_parser, annotation)
    annotation_name = re.sub(r"\W+", "_", str(annotation))
    parser.__name__ = f"parse_{annotation_name}"  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    return parser
