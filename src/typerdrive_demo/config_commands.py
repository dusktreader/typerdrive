"""
Demonstrate how to configure Typerdrive and inspect the effective configuration.
"""

import typer
from typerdrive import add_info_subcommand, set_typerdrive_config


def demo_01__show_app_info():
    """
    Configure client app metadata, then use the `info` command to display it.
    """
    set_typerdrive_config(
        app_name="config-demo",
        version="1.2.3",
        description="A demo app configured with Typerdrive.",
    )
    cli = typer.Typer()
    add_info_subcommand(cli)
    cli(["info"])


def demo_02__show_app_version():
    """
    Show the app name and version with the `version` command.
    """
    set_typerdrive_config(app_name="config-demo", version="1.2.3")
    cli = typer.Typer()
    add_info_subcommand(cli)
    cli(["version"])


def demo_03__show_full_config():
    """
    Use `info --full` to inspect configured values and computed storage paths.
    """
    set_typerdrive_config(
        app_name="config-demo",
        version="1.2.3",
        description="A demo app configured with Typerdrive.",
        log_file_name="config-demo.log",
        console_ascii_only=True,
        console_width=120,
        state_home="tmp/config-demo-state",
        cache_home="tmp/config-demo-cache",
    )
    cli = typer.Typer()
    add_info_subcommand(cli)
    cli(["info", "--full"])
