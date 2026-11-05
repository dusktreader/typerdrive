from typing import Any

from pydantic import BaseModel, ConfigDict
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
    data: dict[str, Any] = {
        "name": "jawa",
        "coloration": {
            "eyes": "yellow",
            "hair": "black",
        },
        "planet": {
            "name": "tatooine",
            "climate": "desert",
        },
    }
    instance: Species = construct_permissive(Species, **data)
    assert instance.name == "jawa"
    assert instance.coloration.eyes == "yellow"
    assert instance.coloration.hair == "black"
    assert instance.planet.name == "tatooine"
    assert instance.planet.climate == "desert"


def test_construct_permissive__allows_missing_values():
    data: dict[str, Any] = {
        "coloration": {
            "eyes": "yellow",
            "hair": "black",
        },
        "planet": {
            "name": "tatooine",
            "climate": "desert",
        },
    }
    instance: Species = construct_permissive(Species, **data)
    assert not hasattr(instance, "name")
    assert instance.coloration.eyes == "yellow"
    assert instance.coloration.hair == "black"
    assert instance.planet.name == "tatooine"
    assert instance.planet.climate == "desert"


def test_construct_permissive__constructs_models_in_supported_collections():
    class FrozenPlanet(BaseModel):
        model_config = ConfigDict(frozen=True)

        name: str

    class CollectionSettings(BaseModel):
        name: str
        colorations: list[Coloration]
        planets: set[FrozenPlanet]
        frozen_planets: frozenset[FrozenPlanet]
        destinations: tuple[Planet, ...]
        planets_by_name: dict[str, Planet]

    data: dict[str, Any] = {
        "colorations": [{"eyes": "yellow", "hair": "black"}],
        "planets": [{"name": "tatooine"}],
        "frozen_planets": [{"name": "mustafar"}],
        "destinations": [{"name": "naboo", "climate": "temperate"}],
        "planets_by_name": {"home": {"name": "tatooine", "climate": "desert"}},
    }
    instance = construct_permissive(CollectionSettings, **data)

    assert not hasattr(instance, "name")
    assert isinstance(instance.colorations[0], Coloration)
    assert isinstance(next(iter(instance.planets)), FrozenPlanet)
    assert isinstance(instance.frozen_planets, frozenset)
    assert isinstance(next(iter(instance.frozen_planets)), FrozenPlanet)
    assert isinstance(instance.destinations[0], Planet)
    assert isinstance(instance.planets_by_name["home"], Planet)
