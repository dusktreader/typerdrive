from typing import Any

from pydantic import BaseModel
from typer_repyt.constants import Sentinel

from typerdrive.settings.exceptions import SettingsError


def construct_permissive[T: BaseModel](model_class: type[T], **values: Any) -> T:
    """
    Construct a model instance permissively.

    Will not raise validation errors if a field is missing or invalid.
    Recursively constructs nested pydantic models.

    Note:
        This function is necessary because `model_construct` does not support nested models.
    """
    constructed_values: dict[str, Any] = {}
    nested_values: dict[str, BaseModel] = {}

    for name, field_info in model_class.model_fields.items():
        key: str = field_info.alias or name
        value: Any = values.get(key, Sentinel.NOT_GIVEN)
        if value is Sentinel.NOT_GIVEN:
            continue
        annotation: type[Any] = SettingsError.enforce_defined(
            field_info.annotation,
            "The field info annotation for {field_info} was not defined!"
        )
        if issubclass(annotation, BaseModel):
            nested_values[key] = construct_permissive(annotation, **value)
        else:
            constructed_values[key] = value

    instance: T = model_class.model_construct(**constructed_values)

    for key, value in nested_values.items():
        setattr(instance, key, value)

    return instance
