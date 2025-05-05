from typing import Annotated

import typer
from pydantic import BaseModel, AfterValidator
from snick import unwrap

from typerdrive.settings.attach import attach_settings


def valid_alignment(value: str) -> str:
    if value not in ["good", "neutral", "evil"]:
        raise ValueError(f"{value} is an invalid alignment")
    return value


class SettingsModel(BaseModel):
    name: str = "jawa"
    planet: str = "tatooine"
    is_humanoid: bool = True
    alignment: Annotated[str, AfterValidator(valid_alignment)] = "neutral"


cli = typer.Typer()


@cli.command()
@attach_settings(SettingsModel)
def report(ctx: typer.Context, cfg: SettingsModel):
    print(
        unwrap(
            f"""
            Look at this {cfg.alignment} {cfg.name} from {cfg.planet}
            {'walking' if cfg.is_humanoid else 'slithering'} by.
            """
        )
    )


if __name__ == "__main__":
    cli()
