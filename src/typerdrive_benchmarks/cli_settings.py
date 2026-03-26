"""
Minimal typerdrive CLI: uses attach_settings only.

Measures the overhead of the most common typerdrive usage pattern.
"""

from typing import Annotated

import typer
from pydantic import AfterValidator, BaseModel

from typerdrive import attach_settings, set_typerdrive_config


def _valid_alignment(value: str) -> str:
    if value not in ["good", "neutral", "evil"]:
        raise ValueError(f"{value} is an invalid alignment")
    return value


class SettingsModel(BaseModel):
    name: str = "jawa"
    planet: str = "tatooine"
    is_humanoid: bool = True
    alignment: Annotated[str, AfterValidator(_valid_alignment)] = "neutral"


cli = typer.Typer()
set_typerdrive_config(app_name="bench-typerdrive-settings")


@cli.command()
@attach_settings(SettingsModel)
def report(ctx: typer.Context, cfg: SettingsModel):
    """Report on a character."""
    walk = "walking" if cfg.is_humanoid else "slithering"
    print(f"Look at this {cfg.alignment} {cfg.name} from {cfg.planet} {walk} by.")


if __name__ == "__main__":
    cli()
