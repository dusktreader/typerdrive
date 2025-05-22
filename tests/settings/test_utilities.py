from typing import Any
from pydantic import BaseModel
from typerdrive.settings.utilities import construct_permissive


class Coloration(BaseModel):
    eyes: str
    hair: str


class Planet(BaseModel):
    name: str
    climate: str


class Species(BaseModel):
    name: str
    coloration: Coloration
    planet: Planet


def test_construct_permissive__basic():
    data: dict[str, Any] = dict(
        name="jawa",
        coloration=dict(
            eyes="yellow",
            hair="black",
        ),
        planet=dict(
            name="tatooine",
            climate="desert",
        ),
    )
    instance: Species = construct_permissive(Species, **data)
    assert instance.name == "jawa"
    assert instance.coloration.eyes == "yellow"
    assert instance.coloration.hair == "black"
    assert instance.planet.name == "tatooine"
    assert instance.planet.climate == "desert"


def test_construct_permissive__allows_missing_values():
    data: dict[str, Any] = dict(
        coloration=dict(
            eyes="yellow",
            hair="black",
        ),
        planet=dict(
            name="tatooine",
            climate="desert",
        ),
    )
    instance: Species = construct_permissive(Species, **data)
    assert not hasattr(instance, "name")
    assert instance.coloration.eyes == "yellow"
    assert instance.coloration.hair == "black"
    assert instance.planet.name == "tatooine"
    assert instance.planet.climate == "desert"
