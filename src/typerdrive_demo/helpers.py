import io
import inspect
from pathlib import Path
import re
import sys
import tempfile
import textwrap
from importlib import import_module
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass

import snick
from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.prompt import Confirm
from rich.markdown import Markdown
from rich.rule import Rule

from typerdrive.env import tweak_env


@dataclass
class Decomposed:
    module: str
    name: str
    docstring: str
    source: str


@dataclass
class Captured:
    error: Exception | None = None
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | str | None = None
    settings: str | None = None


BlankLine = Rule(characters=" ")


def pseudo_clear(console: Console):
    for _ in range(console.size.height):
        console.print(BlankLine)


def fake_input(text: str):
    sys.stdin.write(text)
    sys.stdin.seek(0)


def get_demo_functions(module_name: str) -> list[Callable[..., None]]:
    demo_functions: list[Callable[..., None]] = []
    module = import_module(f"typerdrive_demo.{module_name}")
    for _, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and obj.__name__.startswith("demo"):
            demo_functions.append(obj)
    return sorted(demo_functions, key=lambda f: f.__name__)


def decompose(func: Callable[..., Any]) -> Decomposed:
    """
    This is really hacky.

    Maybe improve this sometime.
    """
    module = func.__module__.split(".")[-1]
    name = func.__name__

    if func.__doc__ is None:
        raise RuntimeError("Can't demo a function with no docstring!")
    docstring = textwrap.dedent(func.__doc__).strip()

    source_lines = inspect.getsourcelines(func)[0]
    first_quotes = False
    code_start_index = 0
    for i, line in enumerate(source_lines):
        if line.strip() == '"""':
            if not first_quotes:
                first_quotes = True
            else:
                code_start_index = i
                break
    if code_start_index == 0:
        raise RuntimeError("Failed to strip function declaration and docstring!")
    source_lines = [re.sub(r"\s+# pyright.*", "", sl) for sl in source_lines]
    source_lines = [re.sub(r"\s+# type.*", "", sl) for sl in source_lines]
    source = textwrap.dedent("".join(source_lines[code_start_index + 1 :]))

    return Decomposed(module=module, name=name, docstring=docstring, source=source)


def capture(demo: Callable[..., None]) -> Captured:
    demo_name = demo.__name__

    cap = Captured()

    stdout_buffer = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = stdout_buffer

    stderr_buffer = io.StringIO()
    original_stderr = sys.stderr
    sys.stderr = stderr_buffer

    stdin_buffer = io.StringIO()
    original_stdin = sys.stdin
    sys.stdin = stdin_buffer

    original_argv = sys.argv
    sys.argv = [demo_name]

    with tempfile.TemporaryDirectory() as fake_home:
        fake_settings_dir = Path(fake_home) / ".local/share" / demo_name
        fake_settings_dir.mkdir(parents=True)
        fake_settings_path = fake_settings_dir / "settings.json"
        with tweak_env(COLUMNS="80", HOME=fake_home):
            try:
                demo()
            except SystemExit as exited:
                cap.exit_code = exited.code
            except Exception as exc:
                cap.error = exc
            finally:
                if fake_settings_path.exists():
                    cap.settings = fake_settings_path.read_text()
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                sys.stdin = original_stdin
                sys.argv = original_argv

    stdout_dump = stdout_buffer.getvalue()
    if stdout_dump:
        cap.stdout = stdout_dump

    stderr_dump = stderr_buffer.getvalue()
    if stderr_dump:
        cap.stderr = stderr_dump

    return cap


def run_demo(demo: Callable[..., None], console: Console, override_label: str | None = None) -> bool:
    pseudo_clear(console)

    decomposed = decompose(demo)
    cap: Captured = capture(demo)

    parts: list[RenderableType] = [
        Markdown(decomposed.docstring),
        BlankLine,
        BlankLine,
        Panel(
            Markdown(
                "\n".join(
                    [
                        "```python",
                        decomposed.source,
                        "```",
                    ]
                )
            ),
            title=f"Here is the source code for [yellow]{decomposed.name}()[/yellow]",
            title_align="left",
            padding=1,
            expand=False,
            box=box.SIMPLE,
        ),
    ]

    if cap.stdout:
        parts.extend(
            [
                BlankLine,
                BlankLine,
                Panel(
                    Markdown(
                        snick.conjoin("```text", cap.stdout, "```"),
                    ),
                    title=f"Here is the stdout captured from [yellow]{decomposed.name}()[/yellow]",
                    title_align="left",
                    padding=1,
                    expand=False,
                    box=box.SIMPLE,
                ),
            ]
        )

    if cap.stderr:
        parts.extend(
            [
                BlankLine,
                BlankLine,
                Panel(
                    Markdown(
                        snick.conjoin("```text", cap.stderr, "```"),
                    ),
                    title=f"Here is the stderr captured from [yellow]{decomposed.name}()[/yellow]",
                    title_align="left",
                    padding=1,
                    expand=False,
                    box=box.SIMPLE,
                ),
            ]
        )

    if cap.error:
        parts.extend(
            [
                BlankLine,
                BlankLine,
                Panel(
                    f"[red]{cap.error.__class__.__name__}[/red]: [yellow]{str(cap.error)}[/yellow]",
                    title=f"Here is the uncaught exception from [yellow]{decomposed.name}()[/yellow]",
                    title_align="left",
                    padding=1,
                    expand=False,
                    box=box.SIMPLE,
                ),
            ]
        )

    if cap.exit_code is not None:
        parts.extend(
            [
                BlankLine,
                BlankLine,
                Panel(
                    Markdown(
                        snick.conjoin("```text", str(cap.exit_code), "```"),
                    ),
                    title=f"Here is the exit code from [yellow]{decomposed.name}()[/yellow]",
                    title_align="left",
                    padding=1,
                    expand=False,
                    box=box.SIMPLE,
                ),
            ]
        )

    if cap.settings is not None:
        parts.extend(
            [
                BlankLine,
                BlankLine,
                Panel(
                    Markdown(
                        snick.conjoin("```json", cap.settings, "```"),
                    ),
                    title=f"Here are the final contents of the settings file from [yellow]{decomposed.name}()[/yellow]",
                    title_align="left",
                    padding=1,
                    expand=False,
                    box=box.SIMPLE,
                ),
            ]
        )

    label = override_label if override_label else f"{decomposed.module}()"
    console.print(
        Panel(
            Group(*parts),
            padding=1,
            title=f"Showing [yellow]{decomposed.name}()[/yellow] for [green]{label}[/green]",
            title_align="left",
            subtitle="[blue]https://github.com/dusktreader/typerdrive[/blue]",
            subtitle_align="left",
        ),
    )
    console.print(BlankLine)
    console.print(BlankLine)
    further: bool = Confirm.ask("Would you like to continue?", default=True)
    return further
