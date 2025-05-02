from enum import StrEnum, auto
import traceback
import logging
import random

from buzz import DoExceptParams
import typer

from typerdrive.exceptions import TyperdriveError, handle_errors
from typerdrive.format import terminal_message, strip_rich_style


class CallIt(StrEnum):
    heads = auto()
    tails = auto()


logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s -> %(message)s'))
logger.addHandler(console_handler)


def log_error(params: DoExceptParams):
    logger.error(
        "\n".join(
            [
                strip_rich_style(params.final_message),
                "--------",
                "Traceback:",
                "".join(traceback.format_tb(params.trace)),
            ]
        )
    )


def log_success():
    logger.info("No errors occurred!")


def log_done():
    logger.info("Program complete. Exiting.")


cli = typer.Typer()


@cli.command()
@handle_errors(
    "Flip error",
    do_except=log_error,
    do_else=log_success,
    do_finally=log_done,
)
def flip(call_it: CallIt, show_logs: bool = False):
    if show_logs:
        logger.setLevel(logging.DEBUG)
    result = random.choice([c for c in CallIt])
    logger.debug(f"Result: {result}")
    if call_it != result:
        raise TyperdriveError(
            f"[yellow]{result}[/yellow], [red]you lose![/red]",
            subject="Womp, womp",
            footer="Don't sweat it; just try again!",
        )
    terminal_message(
        f"[yellow]{result}[/yellow], [green]you win![/green]",
        subject="Tada!",
        footer="Maybe you won't be so lucky next time!",
    )


if __name__ == "__main__":
    cli()
