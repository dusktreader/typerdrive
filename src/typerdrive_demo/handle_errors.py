"""
This set of demos shows the use of the `handle_errors` decorator.
"""

import typer
from buzz import DoExceptParams

from typerdrive.exceptions import TyperdriveError, handle_errors


def demo_1__handle_errors__no_handler():
    """
    This function demonstrates what happens when no handler is installed.
    The output to the user is not nicely formatted. Additionally, in
    actual usage, it includes a stack trace. Generally end-users don't
    find stack-traces to be that helpful.
    """

    cli = typer.Typer()

    @cli.command()
    def report():  # pyright: ignore[reportUnusedFunction]
        raise TyperdriveError("Boring conversation anyway")

    cli()


def demo_2__handle_errors__basic():
    """
    This function demonstrates how to use the `handle_errors` decorator
    to handle `TyperdriveError` exceptions (and all descendants). The
    decorator allows you to capture the errors and print a friendly message
    for the user instead of showing a stack trace.
    """

    cli = typer.Typer()

    @cli.command()
    @handle_errors("What happened?")
    def report():  # pyright: ignore[reportUnusedFunction]
        raise TyperdriveError("Boring conversation anyway")

    cli()


def demo_3__handle_errors__handle_specific_errors():
    """
    This function demonstrates how to use the `handle_errors` decorator
    to handle specific exception types using the `handle_exc_class`
    parameter. Any instance of the supplied exception type will be caught,
    as will any descendant exceptions. You can also provide a group of
    exception types to handle by passing this parameter a tuple of exception
    types.
    """

    cli = typer.Typer()

    @cli.command()
    @handle_errors("What happened?", handle_exc_class=RuntimeError)
    def report():  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("Boring conversation anyway")

    cli()


def demo_4__handle_errors__ignore_specific_errors():
    """
    This function demonstrates how to use the `handle_errors` decorator
    to ignore specific exception types while handling others using the
    `handle_exc_class` and `ignore_exc_class` parameters together. This
    is useful if you want to handle all descendants of a base class but
    ignore one specific descendant class. You can also provide a group of
    exception types to ignore by passing this parameter a tuple of exception
    types.
    """

    cli = typer.Typer()

    class BlasterRuntimeError(RuntimeError):
        pass

    @cli.command()
    @handle_errors(
        "What happened?",
        handle_exc_class=RuntimeError,
        ignore_exc_class=BlasterRuntimeError,
    )
    def report():  # pyright: ignore[reportUnusedFunction]
        raise BlasterRuntimeError("Boring conversation anyway")

    cli()


def demo_5__handle_errors__perform_task_on_error():
    """
    This function demonstrates how to use the `handle_errors` decorator
    to add a task to perform when an exception is handled using the
    `do_except` parameter. The supplied function must take a single
    [`DoExceptParams`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.DoExceptParams)
    argument that carries essential information about the error.
    This kind of extra task is very useful if you want to log the error
    somewhere so that you can inspect it later.
    """

    def fake_logger(params: DoExceptParams):
        print(f"LOGGED: {params.final_message}")

    cli = typer.Typer()

    @cli.command()
    @handle_errors("What happened?", do_except=fake_logger)
    def report():  # pyright: ignore[reportUnusedFunction]
        raise TyperdriveError("Boring conversation anyway")

    cli()


def demo_6__handle_errors__perform_task_with_no_error():
    """
    This function demonstrates how to use the `handle_errors` decorator
    to add a task to perform when no error is handled using the
    `do_else` parameter. The supplied function can't take any
    arguments. This kind of task is less useful than `do_except`,
    but you can find occasional uses for it. In this case, we will "log"
    a message that no error occurred.
    """

    def fake_logger():
        print("LOGGED: No errors occurred!")

    cli = typer.Typer()

    @cli.command()
    @handle_errors("What happened?", do_else=fake_logger)
    def report():  # pyright: ignore[reportUnusedFunction]
        print("We're all fine here now, thank you. How are you?")

    cli()


def demo_7__handle_errors__always_perform_task():
    """
    This function demonstrates how to use the `handle_errors` decorator
    to add a task to _always_ perform whether or not an error is handled
    with the `do_finally` parameter. The supplied function can't take any
    arguments. This kind of task will always be performed at the end of
    the `handle_errors` decorator whether _any_ kind of exception is
    raised or not.
    """

    def fake_logger():
        print("LOGGED: all done!")

    cli = typer.Typer()

    @cli.command()
    @handle_errors("What happened?", do_finally=fake_logger)
    def report():  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("Boring conversation anyway")

    cli()


def demo_8__handle_errors__set_a_subject_and_footer():
    """
    This function demonstrates how to use the `handle_errors` decorator
    with a custom subject and footer that will be displayed with the
    error message.
    """

    cli = typer.Typer()

    @cli.command()
    @handle_errors("What happened?")
    def report():  # pyright: ignore[reportUnusedFunction]
        raise TyperdriveError(
            "Boring conversation anyway",
            subject="slight weapons malfunction",
            footer="WE'RE GONNA HAVE COMPANY!",
        )

    cli()
