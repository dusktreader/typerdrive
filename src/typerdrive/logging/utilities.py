"""
Provide utility functions useful for logging.
"""

from traceback import format_tb
from buzz import DoExceptParams
from loguru import logger

from typerdrive.format import strip_rich_style


def log_error(params: DoExceptParams):
    """
    Log details of an error handled by the `@handle_errors` decorator.

    Parameters:
        params: An instance of `DoExceptParams` that carries the error details.
                See the [`py-byuzz` docs](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.DoExceptParams)
                for more context.
    """
    logger.error(
        "\n".join(
            [
                strip_rich_style(params.final_message),
                "--------",
                "Traceback:",
                "".join(format_tb(params.trace)),
            ]
        )
    )
