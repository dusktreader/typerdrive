from typing import Any, Literal

import snick
from rich.console import Console, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


def terminal_message(
    message: str | RenderableType,
    subject: str | None = None,
    subject_align: Literal["left", "right", "center"] = "left",
    color: str = "green",
    footer: str | None = None,
    footer_align: Literal["left", "right", "center"] = "left",
    indent: bool = True,
    markdown: bool = False,
    error: bool = False,
):
    panel_kwargs: dict[str, Any] = dict(padding=1, title_align=subject_align, subtitle_align=footer_align)
    if subject is not None:
        panel_kwargs["title"] = f"[{color}]{subject}"
    if footer is not None:
        panel_kwargs["subtitle"] = f"[dim italic]{footer}[/dim italic]"
    if isinstance(message, str):
        message = snick.dedent(message)
        if indent:
            message = snick.indent(message, prefix="  ")
        if markdown:
            message = Markdown(message)
    console = Console(stderr=error)
    console.print()
    console.print(Panel(message, **panel_kwargs))
    console.print()


def simple_message(message: str, indent: bool = False, markdown: bool = False, error: bool = False):
    text: str = snick.dedent(message)
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
    if isinstance(text, str):
        text = Text.from_markup(text)
    return text.plain
