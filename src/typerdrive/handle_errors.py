"""
Provide an error handler that can be attached to a command through a decorator.
"""

from typing import ParamSpec, TypeVar
from collections.abc import Callable
from functools import wraps

from buzz import DoExceptParams, get_traceback, reformat_exception
import snick
import typer

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError
from typerdrive.format import terminal_message


P = ParamSpec("P")
T = TypeVar("T")
WrappedFunction = Callable[P, T]


def handle_errors(
    base_message: str,
    *,
    handle_exc_class: type[Exception] | tuple[type[Exception], ...] = TyperdriveError,
    ignore_exc_class: type[Exception] | tuple[type[Exception], ...] | None = None,
    do_except: Callable[[DoExceptParams], None] | None = None,
    do_else: Callable[[], None] | None = None,
    do_finally: Callable[[], None] | None = None,
    unwrap_message: bool = True,
    debug: bool = False,
) -> Callable[[WrappedFunction[P, T]], WrappedFunction[P, T]]:
    """
    Handle errors raised by the decorated command function and show a user-friendly message in the terminal.

    The behavior of this function is _very_ similar to the `py-buzz` `handle_errors()` context manager. See the
    [py-buzz docs](https://dusktreader.github.io/py-buzz/features/#exception-handling-context-manager) for more context.

    Parameters:
        base_message:     The "base" message to be used for the error. This will be the "subject" of the message shown
                          to the user when an error is handled.
        handle_exc_class: The exception class that will be handled. Exception types that inherit from this will also be
                          handled as well.
        ignore_exc_class: An exception class that will _not_ be handled even if it inherits from the `handle_exc_class`.
        do_except:        A function that will be called if an exception is handled. This is most useful for logging
                          the details of the error.
        do_else:          A function that will be called if no exceptions were handled.
        do_finally:       A function that will always be called, even if an exception was handled.
        unwrap_message:   If true, "unwrap" the message so that newline characters are removed.
        debug:            If true, the message shown in the `terminal_message` will include the string representation of
                          the handled error. Not as suitable for end-users, and should only be used for debugging.
    """

    class _DefaultIgnoreException(Exception):
        """
        Define a special exception class to use for the default ignore behavior.

        Basically, this exception type can't be extracted from this method (easily), and thus could never actually
        be raised in any other context. This is only created here to preserve the `try/except/except/else/finally`
        structure.
        """

    ignore_exc_class = _DefaultIgnoreException if ignore_exc_class is None else ignore_exc_class

    def _decorate(func: WrappedFunction[P, T]) -> WrappedFunction[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return_value: T | None = None
            try:
                return_value = func(*args, **kwargs)
            except ignore_exc_class:
                raise
            except handle_exc_class as err:
                try:
                    final_message = reformat_exception(base_message, err)
                except Exception as msg_err:
                    raise RuntimeError(f"Failed while formatting message: {repr(msg_err)}")

                trace = get_traceback()

                if do_except:
                    do_except(
                        DoExceptParams(
                            err=err,
                            base_message=base_message,
                            final_message=final_message,
                            trace=trace,
                        )
                    )

                subject: str | None = base_message
                footer: str | None = None
                message: str

                exit_code: int = ExitCode.GENERAL_ERROR
                if isinstance(err, TyperdriveError):
                    if err.subject:
                        subject = err.subject
                    if err.footer:
                        footer = err.footer
                    if debug:
                        message = err.message
                    else:
                        message = err.base_message or err.message
                    if unwrap_message:
                        message = snick.unwrap(message)
                    exit_code = err.exit_code
                else:
                    message = str(err)

                terminal_message(
                    message,
                    subject=f"[red]{subject}[/red]",
                    footer=footer,
                    error=True,
                )

                raise typer.Exit(code=exit_code)

            else:
                if do_else:
                    do_else()
                return return_value

            finally:
                if do_finally:
                    do_finally()

        return wrapper

    return _decorate
