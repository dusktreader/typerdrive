"""
Full-featured typerdrive CLI: settings + cache + logging + error handling
+ management subcommands.

Measures the worst-case typerdrive startup overhead (all features attached).
"""

from typing import Annotated

import typer
from pydantic import AfterValidator, BaseModel

from typerdrive import (
    add_cache_subcommand,
    add_logs_subcommand,
    add_settings_subcommand,
    attach_cache,
    attach_logging,
    attach_settings,
    handle_errors,
    set_typerdrive_config,
)


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
set_typerdrive_config(app_name="bench-typerdrive-full")


@cli.command()
@handle_errors("Command failed")
@attach_logging()
@attach_cache()
@attach_settings(SettingsModel)
def report(ctx: typer.Context, cfg: SettingsModel):
    """Report on a character."""
    walk = "walking" if cfg.is_humanoid else "slithering"
    print(f"Look at this {cfg.alignment} {cfg.name} from {cfg.planet} {walk} by.")


add_settings_subcommand(cli, SettingsModel)
add_cache_subcommand(cli)
add_logs_subcommand(cli)


if __name__ == "__main__":
    cli()
