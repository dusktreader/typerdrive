"""
Provide utilities for finding encrypted secrets in settings models.
"""

import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from typerdrive.model_parser import is_model_type

_DROP = object()


def _reset_encrypted_value(annotation: Any, value: Any) -> Any:
    """Return `value` with encrypted entries removed, or `_DROP` if the whole value is encrypted."""
    if getattr(annotation, "typerdrive_encrypted", False):
        return _DROP
    if is_model_type(annotation):
        return reset_encrypted_fields(annotation, value) if isinstance(value, dict) else value

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        for option in (arg for arg in args if arg is not type(None)):
            result = _reset_encrypted_value(option, value)
            if result is not value:
                return result
        return value
    if origin in (list, set, frozenset, tuple) and isinstance(value, list):
        item_annotations = [args[0]] * len(value) if args else []
        if origin is tuple and not (len(args) == 2 and args[1] is Ellipsis):
            item_annotations = list(args[: len(value)])
        results = [_reset_encrypted_value(a, item) for a, item in zip(item_annotations, value, strict=False)]
        if any(result is _DROP for result in results):
            return _DROP
        return results + value[len(results) :]
    if origin is dict and isinstance(value, dict) and len(args) > 1:
        results = {key: _reset_encrypted_value(args[1], item) for key, item in value.items()}
        if any(result is _DROP for result in results.values()):
            return _DROP
        return results
    return value


def reset_encrypted_fields(model_class: type[BaseModel], data: dict[str, Any]) -> dict[str, Any]:
    """
    Remove every encrypted field from raw settings data so that those fields fall back to their defaults.

    The fields are found from the model's annotations (including nested models and collections), not from the stored
    values. A collection that holds encrypted values is removed entirely.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        field_info = next(
            (info for name, info in model_class.model_fields.items() if (info.alias or name) == key),
            None,
        )
        if field_info is None:
            result[key] = value
            continue
        reset = _reset_encrypted_value(field_info.annotation, value)
        if reset is not _DROP:
            result[key] = reset
    return result
