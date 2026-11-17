import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, TypeAdapter, ValidationError
from typer_repyt.constants import Sentinel

from typerdrive.model_parser import is_model_collection, is_model_type
from typerdrive.settings.exceptions import SettingsError


def construct_nested_value(annotation: Any, value: Any, context: dict[str, Any] | None = None) -> Any:
    """
    Construct nested model values for a supported annotation.

    Recursively instantiate Pydantic models and rebuild `list`, `set`, `frozenset`, `tuple`, or `dict` containers.
    Encrypted secret values are validated with the given context so that loaded ciphertext is decrypted.
    Leave values unchanged when the input does not match a supported shape.
    """
    if getattr(annotation, "typerdrive_encrypted", False):
        try:
            return TypeAdapter(annotation).validate_python(value, context=context)
        except ValidationError:
            return value

    if is_model_type(annotation):
        if isinstance(value, annotation):
            return value
        if isinstance(value, dict):
            return construct_permissive(annotation, context, **value)
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        options = [arg for arg in args if arg is not type(None)]
        if value is None:
            return value
        for option in options:
            converted = construct_nested_value(option, value, context)
            if converted is not value:
                return converted
        return value
    if origin is list and isinstance(value, list):
        return [construct_nested_value(args[0], item, context) for item in value]
    if origin in (set, frozenset) and isinstance(value, (list, set, frozenset)):
        items = (construct_nested_value(args[0], item, context) for item in value)
        return set(items) if origin is set else frozenset(items)
    if origin is tuple and isinstance(value, (list, tuple)):
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(construct_nested_value(args[0], item, context) for item in value)
        return tuple(
            construct_nested_value(args[index], item, context) if index < len(args) else item
            for index, item in enumerate(value)
        )
    if origin is dict and isinstance(value, dict):
        value_annotation = args[1] if len(args) > 1 else Any
        return {key: construct_nested_value(value_annotation, item, context) for key, item in value.items()}
    return value


def construct_permissive[T: BaseModel](model_class: type[T], context: dict[str, Any] | None = None, **values: Any) -> T:
    """
    Construct a model instance permissively.

    Will not raise validation errors if a field is missing or invalid.
    Recursively constructs nested pydantic models.

    Note:
        This function is necessary because `model_construct` does not support nested models.
    """
    constructed_values: dict[str, Any] = {}
    nested_values: dict[str, Any] = {}

    for name, field_info in model_class.model_fields.items():
        key: str = field_info.alias or name
        value: Any = values.get(key, Sentinel.NOT_GIVEN)
        if value is Sentinel.NOT_GIVEN:
            continue
        annotation: Any = SettingsError.enforce_defined(
            field_info.annotation,
            "The field info annotation for {field_info} was not defined!",
        )
        converted = construct_nested_value(annotation, value, context)
        if is_model_type(annotation) or is_model_collection(annotation):
            nested_values[name] = converted
        else:
            constructed_values[key] = converted

    instance: T = model_class.model_construct(**constructed_values)

    for name, value in nested_values.items():
        setattr(instance, name, value)

    return instance
