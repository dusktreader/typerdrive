# Formatted messages

## Summary

Use the message helpers to present clear output in a Typer CLI, from plain text to a framed panel or operation status.


## Overview

`typerdrive` provides three helpers for output messages:

- `terminal_message` displays content in a Rich panel with an optional subject and footer.
- `simple_message` prints undecorated text, with optional Markdown rendering and indentation.
- `status_message` brackets an operation with starting, completion, and failure lines.

All three functions are available from the `typerdrive` package and are
documented in the [API reference](../reference/base_modules.md).


## Usage

This runnable example defines one command for each message helper:

```python {linenums="1"}
--8<-- "examples/format/messages.py"
```

Run each command from the repository root:

```shell
python examples/format/messages.py terminal
python examples/format/messages.py simple
python examples/format/messages.py status
```

`terminal` displays a panel titled `Connected`, with a footer. `simple` renders a bold Markdown heading and an indented
message without a panel. `status` shows a completed operation followed by a failed operation;
it catches the operation's exception after the failure status is printed.

Install the `demo` extra, then run the interactive message demos:

```shell
typerdrive-demo --feature format
```

See the [demo guide](../demo.md) for installation and interactive controls.


## Details

`terminal_message` accepts a string or any Rich renderable. String messages are dedented and indented by default; set
`markdown=True` to render them as Markdown. Its optional `subject`, `subject_color`, `subject_align`, `footer`, and
`footer_align` arguments customize the panel. Set `error=True` to write to stderr or
`to_clipboard=True` to attempt to copy the message without the panel decoration.

`simple_message` accepts a string and supports the same Markdown, indentation, stderr, and
clipboard options. Its `padding` option controls whether blank lines surround the output.

`status_message` is a context manager. It prints a starting line, then reports completion
or failure. Exceptions are re-raised after the failure status is printed.
