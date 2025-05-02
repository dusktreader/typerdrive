from random import choice

import typer
from rich import print
from rich.panel import Panel
from snick import unwrap

from typerdrive.cache.commands import add_cache_subcommand
from typerdrive.cache.attach import attach_cache, get_manager
from typerdrive.cache.exceptions import CacheError
from typerdrive.env import tweak_env


cli = typer.Typer()
add_cache_subcommand(cli)

speeches = dict(
    yoda=unwrap(
        """
        Size matters not. Look at me. Judge me by my size, do you? Hmm? Hmm. And well you should not. For my ally is the
        Force, and a powerful ally it is. Life creates it, makes it grow. Its energy surrounds us and binds us. Luminous
        beings are we, not this crude matter. You must feel the Force around you; here, between you, me, the tree, the
        rock, everywhere, yes. Even between the land and the ship.
        """
    ),
    leia=unwrap(
        """
        General Kenobi. Years ago you served my father in the Clone Wars. Now he begs you to help him in his struggle
        against the Empire. I regret that I am unable to present my father's request to you in person, but my ship has
        fallen under attack, and now I'm afraid my mission to bring you to Alderaan has failed.  I have placed
        information vital of the survival of the Rebellion into the memory systems of this R2 unit.My father will know
        how to retrieve it. You must see this droid safely delivered to him on Alderaan. This is our most desperate
        hour. Help me, Obi-Wan Kenobi. You're my only hope.
        """
    ),
    han=unwrap(
        """
        Kid, I've flown from one side of this galaxy to the other; I've seen a lot of strange stuff. But I've never seen
        anything to make me believe that there's one all-powerful Force controlling everything. There's no mystical
        energy field that controls my destiny. Anyway, it's all a lot of simple tricks and nonsense.
        """
    )
)


@cli.command()
@attach_cache()
def report(ctx: typer.Context):
    manager = get_manager(ctx)
    speaker = choice(list(speeches.keys()))
    path = f"{speaker}/speech.txt"
    used_cache = False
    text: str
    try:
        text = manager.load_text(path)
    except CacheError:
        print(f"[red]Cache miss![/red] Loading text for {speaker}")
        text = speeches[speaker]
    else:
        print(f"[green]Cache hit![/green] Loaded text from cache target [yellow]{path}[/yellow]")
        used_cache = True

    with tweak_env(COLUMNS="80"):
        print(Panel(text))

    if not used_cache:
        manager.store_text(text, path)
        print(f"Stored text at cache target [yellow]{path}[/yellow]")


if __name__ == "__main__":
    cli()
