"""
Provide methods for formatted output for the user.
"""

from typing import Any, Literal

import pyperclip
import snick
from loguru import logger
from rich import box
from rich.console import Console, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from typerdrive.config import get_typerdrive_config


def _to_clipboard(text: str | RenderableType) -> bool:
    """
    Copy the text to the clipboard if possible.
    """
    try:
        pyperclip.copy(str(text))
        return True
    except Exception as exc:
        logger.debug(f"Could not copy letter to clipboard: {exc}")
        return False


def terminal_message(
    message: RenderableType,
    subject: str | None = None,
    subject_align: Literal["left", "right", "center"] = "left",
    subject_color: str = "green",
    footer: str | None = None,
    footer_align: Literal["left", "right", "center"] = "left",
    indent: bool = True,
    markdown: bool = False,
    error: bool = False,
    to_clipboard: bool = False,
):
    """
    Show a formatted message to the user in a `rich` Panel.

    Parameters:
        message:       The message to show to the user. May be a string or any other `rich.RenderableType`
        subject:       An optional heading for the panel to show to the user
        subject_align: The alignment for the `subject`
        subject_color: The color to render the `subject` in
        footer:        An optional footer to show to the user. If `to_clipboard` results in a successful copy, this will
                       include a message indicating that the message was copied to the clipboard.
        footer_align:  The alignment for the `footer`
        indent:        If `True`, indent all lines of the message by 2 spaces
        markdown:      If `True`, render the text with `rich.markdown`
        error:         If `True`, print the output to stderr instead of stdout
        to_clipboard:  If `True`, attempt to copy the output to the user's clipboard. The text copied to the clipboard
                       will not include the `rich.panel` decoration including the header and footer.
    """
    if to_clipboard:
        if _to_clipboard(message):
            if not footer:
                footer = "Copied to clipboard!"
            else:
                footer = f"{footer} -- Copied to clipboard!"

    panel_kwargs: dict[str, Any] = dict(padding=1, title_align=subject_align, subtitle_align=footer_align)

    if subject is not None:
        panel_kwargs["title"] = f"[{subject_color}]{subject}"

    if footer is not None:
        panel_kwargs["subtitle"] = f"[dim italic]{footer}[/dim italic]"

    if isinstance(message, str):
        message = snick.dedent(message)
        if indent:
            message = snick.indent(message, prefix="  ")
        if markdown:
            message = Markdown(message)

    config = get_typerdrive_config()
    console_kwargs: dict[str, Any] = dict(stderr=error)

    if config.console_width:
        console_kwargs["width"] = config.console_width

    if config.console_ascii_only:
        #console_kwargs["force_terminal"] = False
        panel_kwargs["box"] = box.ASCII

    console = Console(
        stderr=error,

    )
    console.print()
    console.print(Panel(message, **panel_kwargs))
    console.print()


def simple_message(
    message: str,
    indent: bool = False,
    markdown: bool = False,
    error: bool = False,
    to_clipboard: bool = False,
):
    """
    Show a simple, non-decorated message to the user.

    Parameters:
        message:      The message to show to the user; May not be a `rich.RenderableType`
        indent:       If `True`, indent all lines of the message by 2 spaces
        markdown:     If `True`, render the text with `rich.markdown`
        error:        If `True`, print the output to stderr instead of stdout
        to_clipboard: If `True`, attempt to copy the output to the user's clipboard
    """
    text: str = snick.dedent(message)

    if to_clipboard:
        _to_clipboard(text)

    if indent:
        text = snick.indent(text, prefix="  ")

    content: str | Markdown = text

    if markdown:
        content = Markdown(text)

    console = Console(stderr=error)
    console.print()
    console.print(content)
    console.print()


def strip_rich_style(text: str | Text) -> str:
    """
    Strip all rich styling (color, emphasis, etc.) from the text.
    """
    if isinstance(text, str):
        text = Text.from_markup(text)
    return text.plain
