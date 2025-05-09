from typing import Annotated

import typer
from pydantic import AfterValidator, BaseModel
from snick import unwrap
from typerdrive import add_settings_subcommand, attach_settings, set_typerdrive_config


def valid_alignment(value: str) -> str:
    if value not in ["good", "neutral", "evil"]:
        raise ValueError(f"{value} is an invalid alignment")
    return value


class SettingsModel(BaseModel):
    name: str
    planet: str
    is_humanoid: bool = True
    alignment: Annotated[str, AfterValidator(valid_alignment)] = "neutral"


cli = typer.Typer()
add_settings_subcommand(cli, SettingsModel)
set_typerdrive_config(app_name="settings-attach-example")


@cli.command()
@attach_settings(SettingsModel)
def report(ctx: typer.Context, cfg: SettingsModel):
    print(
        unwrap(
            f"""
            Look at this {cfg.alignment} {cfg.name} from {cfg.planet}
            {"walking" if cfg.is_humanoid else "slithering"} by.
            """
        )
    )


if __name__ == "__main__":
    cli()
