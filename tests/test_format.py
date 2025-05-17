import pytest
import snick
from pytest_mock import MockerFixture

from typerdrive.format import simple_message, terminal_message, _to_clipboard  # pyright: ignore[reportPrivateUsage]


def compare_capsys_output(capsys: pytest.CaptureFixture[str], expected_text: str, use_stderr: bool = False):
    if use_stderr:
        computed_text = capsys.readouterr().err
    else:
        computed_text = capsys.readouterr().out
    computed_text = computed_text.strip()
    computed_text = "\n".join(line.rstrip() for line in computed_text.splitlines())
    computed_text = snick.strip_ansi_escape_sequences(computed_text)
    expected_text = snick.dedent(expected_text)
    assert computed_text == expected_text


class TestToClipboard:

    def test__sends_text_to_clipboard(self, mocker: MockerFixture):
        mock_copy = mocker.patch("typerdrive.format.pyperclip.copy")
        message = "Hello, world!"
        assert _to_clipboard(message)
        mock_copy.assert_called_once_with(message)

    def test__returns_false_on_copy_fail(self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture):
        mock_copy = mocker.patch("typerdrive.format.pyperclip.copy")
        mock_copy.side_effect = RuntimeError("Boom!")
        message = "Hello, world!"
        assert not _to_clipboard(message)
        mock_copy.assert_called_once_with(message)
        assert "Could not copy letter to clipboard: Boom!" in caplog.text


class TestTerminalMessage:

    def test__formats_basic_message(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        terminal_message(message)

        compare_capsys_output(capsys, """
            ╭──────────────────────────────────────────────────────────────────────────────╮
            │                                                                              │
            │   Hello, world!                                                              │
            │                                                                              │
            ╰──────────────────────────────────────────────────────────────────────────────╯
        """)

    def test__formats_subject__default_alignment(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        terminal_message(message, subject="Header")

        compare_capsys_output(capsys, """
            ╭─ Header ─────────────────────────────────────────────────────────────────────╮
            │                                                                              │
            │   Hello, world!                                                              │
            │                                                                              │
            ╰──────────────────────────────────────────────────────────────────────────────╯
        """)

    def test__formats_subject__other_alignment(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        terminal_message(message, subject="Header", subject_align="right")

        compare_capsys_output(capsys, """
            ╭───────────────────────────────────────────────────────────────────── Header ─╮
            │                                                                              │
            │   Hello, world!                                                              │
            │                                                                              │
            ╰──────────────────────────────────────────────────────────────────────────────╯
        """)

    def test__formats_footer__default_alignment(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        terminal_message(message, footer="Footer")

        compare_capsys_output(capsys, """
            ╭──────────────────────────────────────────────────────────────────────────────╮
            │                                                                              │
            │   Hello, world!                                                              │
            │                                                                              │
            ╰─ Footer ─────────────────────────────────────────────────────────────────────╯
        """)


    def test__formats_footer__other_alignment(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        terminal_message(message, footer="Footer", footer_align="right")

        compare_capsys_output(capsys, """
            ╭──────────────────────────────────────────────────────────────────────────────╮
            │                                                                              │
            │   Hello, world!                                                              │
            │                                                                              │
            ╰───────────────────────────────────────────────────────────────────── Footer ─╯
        """)


    def test__formats_without_indent(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        terminal_message(message, indent=False)

        compare_capsys_output(capsys, """
            ╭──────────────────────────────────────────────────────────────────────────────╮
            │                                                                              │
            │ Hello, world!                                                                │
            │                                                                              │
            ╰──────────────────────────────────────────────────────────────────────────────╯
        """)

    def test__formats_markdown(self, capsys: pytest.CaptureFixture[str]):
        message = snick.dedent(
            """
            # Hello, world!

            > Here's a quote

            - Item 1
            - Item 2
            - Item 3
            """
        )
        terminal_message(message, markdown=True)

        compare_capsys_output(capsys, """
            ╭──────────────────────────────────────────────────────────────────────────────╮
            │                                                                              │
            │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
            │ ┃                              Hello, world!                               ┃ │
            │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
            │                                                                              │
            │ ▌ Here's a quote                                                             │
            │                                                                              │
            │  • Item 1                                                                    │
            │  • Item 2                                                                    │
            │  • Item 3                                                                    │
            │                                                                              │
            ╰──────────────────────────────────────────────────────────────────────────────╯
        """)

    def test__prints_to_std_error(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        terminal_message(message, error=True)

        compare_capsys_output(
            capsys,
            """
            ╭──────────────────────────────────────────────────────────────────────────────╮
            │                                                                              │
            │   Hello, world!                                                              │
            │                                                                              │
            ╰──────────────────────────────────────────────────────────────────────────────╯
            """,
            use_stderr=True,
        )

    def test__sends_text_to_clipboard(self, mocker: MockerFixture):
        mock__to_clipboard = mocker.patch("typerdrive.format._to_clipboard")
        mock__to_clipboard.return_value = True
        message = "Hello, world!"
        terminal_message(message, to_clipboard=True)

        mock__to_clipboard.assert_called_once_with(message)


class TestSimpleMessage:

    def test__formats_basic_message(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        simple_message(message)

        assert capsys.readouterr().out == snick.conjoin(
            "",
            message,
            "",
            "",
        )

    def test__formats_with_indent(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        simple_message(message, indent=True)

        assert capsys.readouterr().out == snick.conjoin(
            "",
            f"  {message}",
            "",
            "",
        )

    def test__formats_markdown(self, capsys: pytest.CaptureFixture[str]):
        message = snick.dedent(
            """
            # Hello, world!

            > Here's a quote

            - Item 1
            - Item 2
            - Item 3
            """
        )
        simple_message(message, markdown=True)

        compare_capsys_output(capsys, """
            ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
            ┃                                Hello, world!                                 ┃
            ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

            ▌ Here's a quote

             • Item 1
             • Item 2
             • Item 3
        """)

    def test__prints_to_std_error(self, capsys: pytest.CaptureFixture[str]):
        message = "Hello, world!"
        simple_message(message, error=True)

        assert capsys.readouterr().err == snick.conjoin(
            "",
            message,
            "",
            "",
        )

    def test__sends_text_to_clipboard(self, mocker: MockerFixture):
        mock__to_clipboard = mocker.patch("typerdrive.format._to_clipboard")
        mock__to_clipboard.return_value = True
        message = "Hello, world!"
        simple_message(message, to_clipboard=True)

        mock__to_clipboard.assert_called_once_with(message)
