import typer
from typerdrive import add_files_subcommand, attach_files, FilesManager, set_typerdrive_config

cli = typer.Typer()
add_files_subcommand(cli)
set_typerdrive_config(app_name="files-commands-example")


@cli.command()
@attach_files()
def setup(ctx: typer.Context, manager: FilesManager):
    """Set up some example files for demonstration."""

    # Create some configuration files
    manager.store_json({"database": {"host": "localhost", "port": 5432, "name": "myapp"}}, "config/database.json")

    manager.store_json({"api_key": "sk_test_12345", "endpoint": "https://api.example.com"}, "config/api.json")

    # Create some templates
    manager.store_text("Hello {name},\n\nWelcome to our service!\n\nBest regards,\nThe Team", "templates/welcome.txt")

    manager.store_text("<html><body><h1>Welcome {name}!</h1></body></html>", "templates/welcome.html")

    # Create some data files
    manager.store_text("Error: Something went wrong\n", "logs/error.log")
    manager.store_bytes(b"\x89PNG\r\n\x1a\n", "assets/image.png")

    print("Example files created!")
    print("Run 'files show' to see them.")


if __name__ == "__main__":
    cli()
