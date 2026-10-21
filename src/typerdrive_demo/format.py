"""
This set of demos shows the user-facing message functions.
"""

from typerdrive import simple_message, status_message, terminal_message


def demo_1__format__terminal_message():
    """
    Show a structured message in a Rich panel with a subject and footer.
    """

    terminal_message(
        "Your session is ready.",
        subject="Connected",
        footer="Press Ctrl+C to quit",
    )


def demo_2__format__simple_message():
    """
    Show an undecorated message with Markdown formatting and indentation.
    """

    simple_message(
        """
        **Sync complete**

        Three files were updated.
        """,
        markdown=True,
        indent=True,
    )


def demo_3__format__status_message():
    """
    Show status output for both a successful operation and a failed operation.
    """

    with status_message("search index refresh"):
        print("Indexed 3 documents")

    try:
        with status_message("cache refresh"):
            raise RuntimeError("Cache backend unavailable")
    except RuntimeError:
        pass
