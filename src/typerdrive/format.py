"""
Provide methods for formatted output for the user.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Literal, get_args, get_origin

import snick
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from rich import box
from rich.console import Console, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from typerdrive.config import get_typerdrive_config
from typerdrive.exceptions import DisplayError, IntegrationError
from typerdrive.tools import send_to_clipboard


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
        message:       The message to show to the user. May be a string or any other `rich.RenderableType`.
        subject:       An optional heading for the panel to show to the user.
        subject_align: The alignment for the `subject`.
        subject_color: The color to render the `subject` in.
        footer:        An optional footer to show to the user. When `to_clipboard` is enabled, this includes a message
                       indicating that the message was copied to the clipboard.
        footer_align:  The alignment for the `footer`.
        indent:        If `True`, indent all lines of the message by 2 spaces.
        markdown:      If `True`, render the text with `rich.markdown`.
        error:         If `True`, print the output to stderr instead of stdout.
        to_clipboard:  If `True`, copy the output to the user's clipboard and propagate copy errors. The text copied
                       will not include the `rich.panel` decoration including the header and footer.

    Example:
        terminal_message(
            "Three migrations applied.",
            subject="Database setup",
            footer="Ready to launch",
        )
    """
    if to_clipboard:
        try:
            send_to_clipboard(message)
            if not footer:
                footer = "Copied to clipboard!"
            else:
                footer = f"{footer} -- Copied to clipboard!"
        except IntegrationError:
            footer = "Could not copy to clipboard"

    panel_kwargs: dict[str, Any] = {"padding": 1, "title_align": subject_align, "subtitle_align": footer_align}

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
    console_kwargs: dict[str, Any] = {"stderr": error}

    if config.console_width:
        console_kwargs["width"] = config.console_width

    if config.console_ascii_only:
        # console_kwargs["force_terminal"] = False
        panel_kwargs["box"] = box.ASCII

    console = Console(**console_kwargs)
    console.print()
    console.print(Panel(message, **panel_kwargs))
    console.print()


def simple_message(
    message: str,
    indent: bool = False,
    markdown: bool = False,
    error: bool = False,
    to_clipboard: bool = False,
    padding: bool = True,
):
    """
    Show a simple, non-decorated message to the user.

    Parameters:
        message:      The message to show to the user; it cannot be a `rich.RenderableType`.
        indent:       If `True`, indent all lines of the message by 2 spaces.
        markdown:     If `True`, render the text with `rich.markdown`.
        error:        If `True`, print the output to stderr instead of stdout.
        to_clipboard: If `True`, copy the output to the user's clipboard and propagate copy errors.
        padding:      If `True` (default), print a blank line before and after the message.

    Example:
        simple_message("**Sync complete**\n\nThree files were updated.", markdown=True, indent=True)
    """
    text: str = snick.dedent(message)

    if to_clipboard:
        send_to_clipboard(text)

    if indent:
        text = snick.indent(text, prefix="  ")

    content: str | Markdown = text

    if markdown:
        content = Markdown(text)

    console = Console(stderr=error)
    if padding:
        console.print()
    console.print(content)
    if padding:
        console.print()


@contextmanager
def status_message(action: str, error: bool = False) -> Generator[None, None, None]:
    """
    Print status lines before and after an operation.

    Parameters:
        action: A short description of the operation being performed (should start with lower-case).
        error:  If `True`, print all output to stderr instead of stdout.

    Example:
        with status_message("database migrations"):
            run_migrations()

        with status_message("cache refresh"):
            refresh_cache()

        The first operation prints a completion line. If either operation raises an exception, the context manager prints
        a failure line and re-raises the exception.
    """
    console = Console(stderr=error)
    console.print(f"[bold blue]→[/bold blue] Starting {action}...")
    try:
        yield
    except Exception:
        console.print(f"[bold red]✗[/bold red] Failed {action}")
        raise
    else:
        console.print(f"[bold green]✓[/bold green] Completed {action}")


def strip_rich_style(text: str | Text) -> str:
    """
    Strip all rich styling (color, emphasis, etc.) from the text.
    """
    if isinstance(text, str):
        text = Text.from_markup(text)
    return text.plain


def pretty_model(model_class: type[BaseModel]) -> str:
    """
    Format a pydantic model class.
    """
    parts: list[str] = [f"{fn}={pretty_field_info(fi)}" for (fn, fi) in model_class.model_fields.items()]
    return f"{model_class.__name__}({' '.join(parts)})"


def pretty_annotation(annotation: Any) -> str:
    """Format built-in collection annotations and their type arguments for display."""
    origin = get_origin(annotation)
    if origin in (list, set, frozenset, tuple, dict):
        args = get_args(annotation)
        arg_names = ["..." if arg is Ellipsis else pretty_annotation(arg) for arg in args]
        return f"{origin.__name__}[{', '.join(arg_names)}]"
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)


def pretty_field_info(field_info: FieldInfo) -> str:
    """
    Format a Pydantic FieldInfo.
    """
    annotation = DisplayError.enforce_defined(
        field_info.annotation, f"The field info annotation for {field_info} was not defined!"
    )
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return pretty_model(annotation)
    return pretty_annotation(annotation)
