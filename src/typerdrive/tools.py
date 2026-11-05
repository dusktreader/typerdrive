import pyperclip
from rich.console import RenderableType

from typerdrive.exceptions import IntegrationError


def send_to_clipboard(text: str | RenderableType) -> None:
    """Send the text to the system clipboard."""
    from typerdrive.logging.utilities import log_error

    with IntegrationError.handle_errors("Could not send text to clipboard", do_except=log_error):
        pyperclip.copy(str(text))
