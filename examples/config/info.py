import typer
from typerdrive import add_info_subcommand, set_typerdrive_config


set_typerdrive_config(
    app_name="config-example",
    version="1.2.3",
    description="Demonstrate Typerdrive configuration.",
    log_file_name="config-example.log",
    console_ascii_only=True,
    console_width=100,
    state_home="/tmp/typerdrive-docs-state",
    cache_home="/tmp/typerdrive-docs-cache",
)

cli = typer.Typer()
add_info_subcommand(cli)


if __name__ == "__main__":
    cli()
