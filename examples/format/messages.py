import typer
from typerdrive import simple_message, status_message, terminal_message

cli = typer.Typer()


@cli.command()
def terminal():
    terminal_message(
        "Your session is ready.",
        subject="Connected",
        footer="Press Ctrl+C to quit",
    )


@cli.command()
def simple():
    simple_message(
        """
        **Sync complete**

        Three files were updated.
        """,
        markdown=True,
        indent=True,
    )


@cli.command()
def status():
    with status_message("search index refresh"):
        print("Indexed 3 documents")

    try:
        with status_message("cache refresh"):
            raise RuntimeError("Cache backend unavailable")
    except RuntimeError:
        pass


if __name__ == "__main__":
    cli()
