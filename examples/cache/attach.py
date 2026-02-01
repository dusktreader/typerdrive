import typer
from typerdrive import CacheManager, attach_cache

cli = typer.Typer()


@cli.command()
@attach_cache()
def report(ctx: typer.Context, manager: CacheManager):  # pyright: ignore[reportUnusedParameter]
    key = "jawa/ewok"

    # Get from cache, or set default if not found
    text = manager.setdefault(key, "Never will you find a more wretched hive of scum and villainy.")

    print(f"Text: {text}")


if __name__ == "__main__":
    cli()
