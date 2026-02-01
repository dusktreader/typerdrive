"""
This set of demos shows the use of the `attach_files` decorator.
"""

import typer
from rich import print
from typerdrive import (
    FilesManager,
    attach_files,
    get_files_manager,
    set_typerdrive_config,
)

set_typerdrive_config(app_name="attach-files-demo")


def demo_1__attach_files__storing_data():
    """
    This function demonstrates how to use the `attach_files` decorator
    to store data. The decorator gives you access to the `FilesManager`
    within a typer command by adding a parameter with `FilesManager` type.
    The `FilesManager` can store bytes, text, or JSON data.
    """

    cli = typer.Typer()

    @cli.command()
    @attach_files(show=True)
    def store(ctx: typer.Context, manager: FilesManager):
        # Store text files
        manager.store_text("The Force will be with you. Always.", "quotes/obi-wan.txt")
        manager.store_text("Do or do not. There is no try.", "quotes/yoda.txt")

        # Store JSON configuration
        manager.store_json(
            {"character": "Yoda", "age": 900, "quotes": ["Do or do not", "Size matters not"]}, "characters/yoda.json"
        )

        # Store binary data
        manager.store_bytes(b"\x89PNG\r\n\x1a\n", "images/jedi.png")

        print("[green]Files stored successfully![/green]")

    cli()


def demo_2__attach_files__loading_data():
    """
    This function demonstrates how to load data from files.
    First we pre-populate some files, then load them back.
    """

    # Pre-populate files
    manager = FilesManager()
    manager.store_text("Hello from Tatooine!", "message.txt")
    manager.store_json({"planet": "Tatooine", "moons": 2}, "data.json")
    manager.store_bytes(b"Binary data", "data.bin")

    cli = typer.Typer()

    @cli.command()
    @attach_files(show=True)
    def load(ctx: typer.Context, manager: FilesManager):
        # Load text
        message = manager.load_text("message.txt")
        print(f"[cyan]Message:[/cyan] {message}")

        # Load JSON
        data = manager.load_json("data.json")
        print(f"[cyan]Planet:[/cyan] {data['planet']}")
        print(f"[cyan]Moons:[/cyan] {data['moons']}")

        # Load bytes
        binary = manager.load_bytes("data.bin")
        print(f"[cyan]Binary:[/cyan] {binary!r}")

    cli()


def demo_3__attach_files__with_permissions():
    """
    This function demonstrates storing files with specific permissions.
    This is useful for sensitive data like API keys or credentials.
    """

    cli = typer.Typer()

    @cli.command()
    @attach_files(show=True)
    def store_secret(ctx: typer.Context, manager: FilesManager):
        # Store with owner-only read/write permissions (0o600)
        secret = {"api_key": "sk_live_super_secret_key_12345"}
        manager.store_json(secret, "secrets/api_key.json", mode=0o600)

        print("[yellow]Secret stored with restricted permissions (0o600)[/yellow]")
        print("[dim]Only the owner can read or write this file[/dim]")

    cli()


def demo_4__attach_files__list_and_manage():
    """
    This function demonstrates listing files in a directory
    and managing them programmatically.
    """

    # Pre-populate with multiple files
    manager = FilesManager()
    manager.store_text("Template 1", "templates/welcome.txt")
    manager.store_text("Template 2", "templates/goodbye.txt")
    manager.store_text("Template 3", "templates/reminder.txt")

    cli = typer.Typer()

    @cli.command()
    @attach_files()
    def list_templates(ctx: typer.Context, manager: FilesManager):
        # List all templates
        templates = manager.list_items("templates")

        print(f"[cyan]Found {len(templates)} templates:[/cyan]")
        for template_name in sorted(templates):
            print(f"  • {template_name}")

    cli()


def demo_5__attach_files__access_through_context():
    """
    This function demonstrates how the files manager can also be accessed
    through the Typer context if you do not want to use a `FilesManager`
    parameter. To access the manager with the context, use the
    `get_files_manager()` helper function.
    """

    cli = typer.Typer()

    @cli.command()
    @attach_files(show=True)
    def store(ctx: typer.Context):
        # Get manager from context
        manager = get_files_manager(ctx)

        manager.store_text("Accessed via context!", "context_example.txt")
        manager.store_json({"method": "context"}, "metadata.json")

        print("[green]Files stored using context-retrieved manager![/green]")

    cli()
