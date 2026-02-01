import typer
from typerdrive import attach_files, FilesManager, set_typerdrive_config

cli = typer.Typer()
set_typerdrive_config(app_name="files-attach-example")


@cli.command()
@attach_files()
def store(ctx: typer.Context, manager: FilesManager):  # pyright: ignore[reportUnusedParameter]
    """Store various types of data in files."""

    # Store text
    greeting = "Hello from the files feature!"
    manager.store_text(greeting, "greeting.txt")
    print(f"Stored text at greeting.txt")

    # Store JSON
    config = {"app_name": "My Awesome CLI", "version": "1.0.0", "features": ["auth", "api", "database"]}
    manager.store_json(config, "config/app.json")
    print(f"Stored JSON at config/app.json")

    # Store bytes
    binary_data = b"This is binary data: \x00\x01\x02\x03"
    manager.store_bytes(binary_data, "data/binary.dat")
    print(f"Stored bytes at data/binary.dat")


@cli.command()
@attach_files()
def load(ctx: typer.Context, manager: FilesManager):  # pyright: ignore[reportUnusedParameter]
    """Load data from files."""

    # Load text
    greeting = manager.load_text("greeting.txt")
    print(f"Greeting: {greeting}")

    # Load JSON
    config = manager.load_json("config/app.json")
    print(f"App name: {config['app_name']}")
    print(f"Version: {config['version']}")
    print(f"Features: {', '.join(config['features'])}")

    # Load bytes
    binary_data = manager.load_bytes("data/binary.dat")
    print(f"Binary data (first 10 bytes): {binary_data[:10]}")


@cli.command()
@attach_files(show=True)
def demo(ctx: typer.Context, manager: FilesManager):  # pyright: ignore[reportUnusedParameter]
    """Store some data and show the files directory."""

    manager.store_text("The Force will be with you. Always.", "quotes/obi-wan.txt")
    manager.store_text("Do or do not. There is no try.", "quotes/yoda.txt")
    manager.store_json({"character": "Yoda", "age": 900, "species": "Unknown"}, "characters/yoda.json")

    print("Files stored!")
    # Files directory will be shown automatically due to show=True


if __name__ == "__main__":
    cli()
