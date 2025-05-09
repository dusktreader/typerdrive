from typing import Annotated

import typer
from pydantic import BaseModel
from typerdrive import (
    TyperdriveClient,
    attach_client,
    attach_settings,
    handle_errors,
    set_typerdrive_config,
    terminal_message,
)


class SettingsModel(BaseModel):
    people_url: str = "https://swapi.info/api/people"
    planets_url: str = "https://swapi.info/api/planets"


class PeopleResponse(BaseModel, extra="ignore"):
    name: str
    height: int
    birth_year: str
    gender: str


class PlanetResponse(BaseModel, extra="ignore"):
    name: str
    climate: str
    terrain: str
    gravity: str
    population: int


cli = typer.Typer()
set_typerdrive_config(app_name="cache-commands-example")


@cli.command()
@handle_errors("Lookup on SWAPI failed!")
@attach_settings(SettingsModel)
@attach_client(people="people_url", planets="planets_url")
def report(
    ctx: typer.Context,  # pyright: ignore[reportUnusedParameter]
    people: TyperdriveClient,
    planets: TyperdriveClient,
    person_id: Annotated[int, typer.Option(help="The ID of the person to look up")] = 1,
    planet_id: Annotated[int, typer.Option(help="The ID of the planet to look up")] = 1,
):
    terminal_message(
        str(people.get_x(f"{person_id}", expected_status=200, response_model=PeopleResponse)),
        subject=f"Person {person_id}",
        footer=f"Fetched from {people.base_url}{person_id}",
    )
    terminal_message(
        str(planets.get_x(f"{planet_id}", expected_status=200, response_model=PlanetResponse)),
        subject=f"Planet {planet_id}",
        footer=f"Fetched from {planets.base_url}{planet_id}",
    )


if __name__ == "__main__":
    cli()
