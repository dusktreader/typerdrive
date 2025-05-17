"""
Provide exception types for `typerdrive`.

All exception types derived from `TyperdriveError` will, by default, be handled by the `@handle_errors` decorator.
"""

from typing import Any

from buzz import Buzz
from rich import traceback

from typerdrive.constants import ExitCode

traceback.install()


class TyperdriveError(Buzz):
    """
    Base exception class for all `typerdrive` errors.

    Derives from the `buzz.Buzz` base class. See the
    [`py-buzz` docs](https://dusktreader.github.io/py-buzz/features/#the-buzz-base-class) to learn more.
    """

    subject: str | None = None
    """ The subject to show on user-facing messages when this error is handled by `@handle_errors()` """

    footer: str | None = None
    """ The footer to show on user-facing messages when this error is handled by `@handle_errors()` """

    exit_code: ExitCode = ExitCode.GENERAL_ERROR
    """ The exit code that should be used after handling the error and terminating the app """

    details: Any | None = None
    """ Any additional details that should be included in the error as well """

    def __init__(
        self,
        *args: Any,
        subject: str | None = None,
        footer: str | None = None,
        details: Any | None = None,
        exit_code: ExitCode | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        if subject:
            self.subject = subject
        if footer:
            self.footer = footer
        if details:
            self.details = details
        if exit_code:
            self.exit_code = exit_code


class ContextError(TyperdriveError):
    """
    Indicates that there was a problem interacting with the `Typer.Context`.
    """
    exit_code: ExitCode = ExitCode.INTERNAL_ERROR


class BuildCommandError(TyperdriveError):
    """
    Indicates that there was a problem building a command with `typer-repyt`.
    """
    exit_code: ExitCode = ExitCode.INTERNAL_ERROR
