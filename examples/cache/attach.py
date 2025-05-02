import typer

from typerdrive.cache.attach import attach_cache, get_manager
from typerdrive.cache.exceptions import CacheError


cli = typer.Typer()


@cli.command()
@attach_cache()
def report(ctx: typer.Context):
    manager = get_manager(ctx)
    path = "jawa/ewok.txt"
    text: str
    try:
        text = manager.load_text(path)
    except CacheError:
        print("Cache miss! Created new text")
        text = "Never will you find a more wretched hive of scum and villainy."
    else:
        print(f"Cache hit! Loaded text from cache target {path}")

    print(f"Text: {text}")
    manager.store_text(text, path)
    print(f"Stored text at cache target {path}")


if __name__ == "__main__":
    cli()
