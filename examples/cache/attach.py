import typer
from typerdrive import CacheError, CacheManager, attach_cache

cli = typer.Typer()


@cli.command()
@attach_cache()
def report(ctx: typer.Context, manager: CacheManager):  # pyright: ignore[reportUnusedParameter]
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
