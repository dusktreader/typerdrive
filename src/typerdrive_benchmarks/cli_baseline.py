"""
Baseline CLI: plain typer + pydantic, no typerdrive.

Used as the zero-overhead reference point for all startup benchmarks.
"""

from typing import Annotated

import typer
from pydantic import AfterValidator, BaseModel


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


@cli.command()
def report(
    name: str = "jawa",
    planet: str = "tatooine",
    is_humanoid: bool = True,
):
    """Report on a character."""
    cfg = SettingsModel(name=name, planet=planet, is_humanoid=is_humanoid)
    walk = "walking" if cfg.is_humanoid else "slithering"
    print(f"Look at this {cfg.name} from {cfg.planet} {walk} by.")


if __name__ == "__main__":
    cli()
