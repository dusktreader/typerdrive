"""Provide a Roadshow `demo` decorator that isolates typerdrive's config and storage for each demo."""

import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

import click.termui
from roadshow import DemoFunction
from roadshow import demo as roadshow_demo
from typerdrive.config import get_typerdrive_config, set_typerdrive_config


def _stdin_hidden_prompt(prompt: str) -> str:
    """Read hidden input from stdin so that demos never wait on the controlling terminal (as `getpass` would)."""
    print(prompt)
    return sys.stdin.readline().rstrip("\n")


def demo(
    feature: str,
    *,
    input_text: str | None = None,
    input_lines: Sequence[str] | None = None,
    argv: Sequence[str] = (),
) -> Callable[[DemoFunction], DemoFunction]:
    """Mark a function as a demo whose typerdrive state lives in a temporary directory."""
    original_config = get_typerdrive_config()
    original_prompt = click.termui.hidden_prompt_func
    directories: list[tempfile.TemporaryDirectory[str]] = []

    def isolate() -> None:
        directory = tempfile.TemporaryDirectory(prefix="typerdrive-demo-")
        directories.append(directory)
        setattr(click.termui, "hidden_prompt_func", _stdin_hidden_prompt)
        home = Path(directory.name)
        set_typerdrive_config(
            app_name=feature.replace("_", "-"),
            state_home=home / ".local" / "state",
            cache_home=home / ".cache",
        )

    def restore() -> None:
        setattr(click.termui, "hidden_prompt_func", original_prompt)
        set_typerdrive_config(**original_config.model_dump())
        while directories:
            directories.pop().cleanup()

    return roadshow_demo(
        feature, before=isolate, after=restore, input_text=input_text, input_lines=input_lines, argv=argv
    )
