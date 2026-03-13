from io import StringIO

from rich.console import Console
from rich.tree import Tree
from snick import strip_ansi_escape_sequences


def tree_to_text(tree: Tree) -> str:
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=80)
    console.print(tree)
    return strip_ansi_escape_sequences(buffer.getvalue()).strip()
