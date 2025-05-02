from itertools import pairwise
import re
from typing import Any

import typer
from snick import conjoin, strip_ansi_escape_sequences, strip_whitespace, dedent, indent
from typer.testing import CliRunner


runner = CliRunner()


def strip_lineart(text: str) -> str:
    lineart = ["╭", "─", "┬", "╮", "│", "├", "┼", "┤", "╰", "┴", "╯", "└"]
    for char in lineart:
        text = text.replace(char, "")
    return text


def get_output(
    cli: typer.Typer,
    *args: str,
    exit_code: int = 0,
    env_vars: dict[str, str] | None = None,
    strip_terminal_controls: bool = True,
    exception_type: type[Exception] | None = None,
    exception_pattern: str | None = None,
    **kwargs: Any,
) -> str:
    if env_vars is None:
        env_vars = {}
    result = runner.invoke(cli, args, env=env_vars, **kwargs)
    output = result.stdout
    if strip_terminal_controls:
        output = strip_ansi_escape_sequences(output)
    assert result.exit_code == exit_code, build_code_fail_message(exit_code, result.exit_code, output, result.exception)
    if exception_type:
        assert isinstance(result.exception, exception_type), build_exception_type_message(
            result.exception,
            exception_type,
            output,
        )
    if exception_pattern:
        assert re.search(exception_pattern, str(result.exception)), build_exception_pattern_message(
            result.exception,
            exception_pattern,
            output,
        )

    return output


def get_help(cli: typer.Typer) -> str:
    return get_output(cli, "--help")


def check_output(
    cli: typer.Typer,
    *args: str,
    expected_substring: str | list[str] | None = None,
    unwanted_substring: str | list[str] | None = None,
    **kwargs: Any,
):
    output = get_output(cli, *args, **kwargs)
    if expected_substring:
        if isinstance(expected_substring, str):
            expected_substring = [expected_substring]
        for es in expected_substring:
            assert es in output, build_substring_fail_message(es, output)
    if unwanted_substring:
        if isinstance(unwanted_substring, str):
            unwanted_substring = [unwanted_substring]
        for us in unwanted_substring:
            assert us not in output, build_substring_fail_message(us, output, negative_match=True)


def check_help(cli: typer.Typer, **kwargs: Any):
    check_output(cli, "--help", exit_code=0, **kwargs)


def match_output(
    cli: typer.Typer,
    *args: str,
    expected_pattern: str | list[str] | None = None,
    unwanted_pattern: str | list[str] | None = None,
    enforce_order: bool = True,
    escape_parens: bool = False,
    escape_brackets: bool = False,
    **kwargs: Any,
):
    output = get_output(cli, *args, **kwargs)
    if expected_pattern:
        if isinstance(expected_pattern, str):
            expected_pattern = [expected_pattern]

        start_positions: list[int] = []
        for ep in expected_pattern:
            mangled_pattern = ep
            mangled_pattern = strip_lineart(strip_whitespace(mangled_pattern))
            if escape_parens:
                mangled_pattern = mangled_pattern.replace("(", r"\(").replace(")", r"\)")
            if escape_brackets:
                mangled_pattern = mangled_pattern.replace("[", r"\[").replace("]", r"\]")

            mangled_output = output
            mangled_output = strip_lineart(strip_whitespace(mangled_output))

            match: re.Match[str] | None = re.search(mangled_pattern, mangled_output)
            if match is not None:
                start_positions.append(match.start())

            assert match, build_pattern_fail_message(ep, mangled_pattern, output, mangled_output)

        if enforce_order:
            assert all(left <= right for (left, right) in pairwise(start_positions)), build_order_fail_message(
                expected_pattern, start_positions, output
            )

    if unwanted_pattern:
        if isinstance(unwanted_pattern, str):
            unwanted_pattern = [unwanted_pattern]

        for up in unwanted_pattern:
            mangled_pattern = up
            mangled_pattern = strip_lineart(strip_whitespace(mangled_pattern))
            if escape_parens:
                mangled_pattern = mangled_pattern.replace("(", r"\(").replace(")", r"\)")
            if escape_brackets:
                mangled_pattern = mangled_pattern.replace("[", r"\[").replace("]", r"\]")

            mangled_output = output
            mangled_output = strip_lineart(strip_whitespace(mangled_output))

            assert not re.search(mangled_pattern, mangled_output), build_pattern_fail_message(
                up,
                mangled_pattern,
                output,
                mangled_output,
                negative_pattern=True,
            )


def match_help(
    cli: typer.Typer,
    **kwargs: Any,
):
    match_output(cli, "--help", exit_code=0, **kwargs)


def build_code_fail_message(
    expected_code: int,
    computed_code: int,
    output: str,
    exception: BaseException | None,
) -> str:
    return dedent(
        f"""
        Exit codes didn't match!

        Expected {expected_code}
        Computed {computed_code}

        Exception:
        {exception}

        Output:
        {indent(output, prefix="            ", skip_first_line=True)}
        """
    )


def build_exception_type_message(
    exception: BaseException | None,
    exception_type: type[Exception],
    output: str,
) -> str:
    return dedent(
        f"""
        Expected exception type doesn't match!

        Expected {exception_type}
        Computed {type[exception]}

        Exception:
        {exception}

        Output:
        {indent(output, prefix="            ", skip_first_line=True)}
        """
    )


def build_exception_pattern_message(
    exception: BaseException | None,
    exception_pattern: str,
    output: str,
) -> str:
    return dedent(
        f"""
        Expected exception text doesn't match pattern!

        Expected {exception_pattern}
        Computed {exception}

        Output:
        {indent(output, prefix="            ", skip_first_line=True)}
        """
    )


def build_substring_fail_message(
    substring: str,
    output: str,
    negative_match: bool = False,
) -> str:
    qualifier = "was not found" if not negative_match else "WAS FOUND"
    return dedent(
        f"""
        Substring {qualifier} in output

        Substring:
        {substring}

        Output:
        {indent(output, prefix="            ", skip_first_line=True)}
        """
    )


def build_pattern_fail_message(
    pattern: str,
    mangled_pattern: str,
    output: str,
    mangled_output: str,
    negative_pattern: bool = False,
) -> str:
    qualifier = "was not found" if not negative_pattern else "WAS FOUND"
    return dedent(
        f"""
        Search pattern {qualifier} in output

        Search Pattern:
        {pattern}

        "Mangled" Search Pattern:
        {repr(mangled_pattern)}

        Output:
        {indent(output, prefix="            ", skip_first_line=True)}

        "Mangled" Output:
        {repr(mangled_output)}
        """
    )


def build_order_fail_message(expected_patterns: list[str], start_positions: list[int], output: str) -> str:
    return conjoin(
        "Search patterns were out of order",
        "",
        *[f"{i}: {p}" for (i, p) in zip(start_positions, expected_patterns)],
        "",
        "Output:",
        output,
    )
