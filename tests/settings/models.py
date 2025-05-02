from typing import Annotated

from pydantic import AfterValidator, BaseModel


def valid_alignment(value: str) -> str:
    if value not in ["good", "neutral", "evil"]:
        raise ValueError(f"{value} is an invalid alignment")
    return value


class DefaultSettingsModel(BaseModel):
    name: str = "jawa"
    planet: str = "tatooine"
    is_humanoid: bool = True
    alignment: Annotated[str, AfterValidator(valid_alignment)] = "neutral"


class RequiredFieldsModel(BaseModel):
    name: str
    planet: str
    is_humanoid: bool = True
    alignment: Annotated[str, AfterValidator(valid_alignment)] = "neutral"
