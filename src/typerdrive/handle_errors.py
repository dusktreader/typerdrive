"""
Provide an error handler that can be attached to a command through a decorator.
"""

from collections.abc import Awaitable, Callable
from inspect import isawaitable, iscoroutinefunction
from typing import NoReturn, ParamSpec, TypeVar, cast

from buzz import DoExceptParams, get_traceback, reformat_exception
import snick
import typer

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError
from typerdrive.format import terminal_message
from typerdrive.signature import SignatureRewriter


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
        rewriter = SignatureRewriter(func)

        def handle_error(err: Exception) -> NoReturn:
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
            if isinstance(err, TyperdriveError):
                if err.subject:
                    subject = err.subject
                if err.footer:
                    footer = err.footer
                message = err.message if debug else err.base_message or err.message
                if unwrap_message:
                    message = snick.unwrap(message)
                exit_code = err.exit_code
            else:
                message = str(err)
                exit_code = ExitCode.GENERAL_ERROR

            terminal_message(message, subject=f"[red]{subject}[/red]", footer=footer, error=True)
            raise typer.Exit(code=exit_code)

        async def await_result(awaitable: Awaitable[T]) -> T:
            try:
                result = await awaitable
            except ignore_exc_class:
                raise
            except handle_exc_class as err:
                handle_error(cast(Exception, err))
            else:
                if do_else:
                    do_else()
                return result
            finally:
                if do_finally:
                    do_finally()

        if iscoroutinefunction(func):
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                return await await_result(cast(Awaitable[T], func(*args, **kwargs)))
        else:
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                return_value: T | Awaitable[T] | None = None
                try:
                    return_value = func(*args, **kwargs)
                    if isawaitable(return_value):
                        return cast(T, await_result(cast(Awaitable[T], return_value)))
                except ignore_exc_class:
                    raise
                except handle_exc_class as err:
                    handle_error(cast(Exception, err))
                else:
                    if do_else:
                        do_else()
                    return cast(T, return_value)
                finally:
                    if not isawaitable(return_value) and do_finally:
                        do_finally()

        rewriter.apply(wrapper)
        return cast(WrappedFunction[P, T], wrapper)

    return _decorate
