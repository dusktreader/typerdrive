"""
This set of demos shows the use of the `@attach_client()` decorator.
"""

from random import randint

import typer
from pydantic import BaseModel
from rich import print
from typerdrive import TyperdriveClient, attach_client, attach_settings


def demo_1__attach_client__use_base_url_from_settings():
    """
    This function demonstrates how to use the `@attach_client()` decorator
    to attach a client to the app context using a base_url from the attached
    settings. The client provided is a TyperdriveClient that includes the
    enhanced "x" methods. In this example, `get_x()` is used to deserialize
    the response into a pydantic model. The `base_url` to use for the client
    is pulled from the matching field in the settings.
    """

    class SettingsModel(BaseModel):
        base_url: str = "https://swapi.info/api/people"

    class ResponseModel(BaseModel, extra="ignore"):
        name: str
        height: int
        mass: int
        birth_year: str
        gender: str

    cli = typer.Typer()

    @cli.command()
    @attach_settings(SettingsModel)
    @attach_client(swapi="base_url")
    def report(ctx: typer.Context, swapi: TyperdriveClient):  # pyright: ignore[reportUnusedFunction, reportUnusedParameter]
        person_id = randint(1, 10)
        print(f"Person {person_id} ->", swapi.get_x(f"{person_id}", response_model=ResponseModel))

    cli()


def demo_2__attach_client__use_explicit_base_url():
    """
    This function demonstrates how a client can be initialized without
    settings if the full base_url is provided.
    """

    class ResponseModel(BaseModel, extra="ignore"):
        name: str
        height: int
        mass: int
        birth_year: str
        gender: str

    cli = typer.Typer()

    @cli.command()
    @attach_client(swapi="https://swapi.info/api/people")
    def report(ctx: typer.Context, swapi: TyperdriveClient):  # pyright: ignore[reportUnusedFunction, reportUnusedParameter]
        person_id = randint(1, 10)
        print(f"Person {person_id} ->", swapi.get_x(f"{person_id}", response_model=ResponseModel))

    cli()


def demo_3__attach_client__multiple_clients():
    """
    This function demonstrates how multiple clients may be attached.
    The clients are independent of each other.
    """

    class SettingsModel(BaseModel):
        people_url: str = "https://swapi.info/api/people"
        planets_url: str = "https://swapi.info/api/planets"

    class PeopleResponse(BaseModel, extra="ignore"):
        name: str
        height: int
        mass: int
        birth_year: str
        gender: str

    class PlanetResponse(BaseModel, extra="ignore"):
        name: str
        climate: str
        terrain: str
        gravity: str
        population: int

    cli = typer.Typer()

    @cli.command()
    @attach_settings(SettingsModel)
    @attach_client(
        people="people_url",
        planets="planets_url",
    )
    def report(ctx: typer.Context, people: TyperdriveClient, planets: TyperdriveClient, id: int = 1):  # pyright: ignore[reportUnusedFunction, reportUnusedParameter]
        person_id = randint(1, 10)
        planet_id = randint(1, 10)

        print(f"Person {person_id} ->", people.get_x(f"{person_id}", response_model=PeopleResponse))
        print(f"Planet {planet_id} ->", planets.get_x(f"{planet_id}", response_model=PlanetResponse))

    cli()
