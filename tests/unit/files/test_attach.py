"""
Tests for `attach_files` decorator.
"""

from pathlib import Path

from tests.unit.files.string_annotation_module import (
    make_string_annotated_cli,
    make_string_annotated_manager_cli,
)
from tests.unit.helpers import match_output


class TestStringAnnotations:
    """
    Verify that `attach_files` works correctly when the decorated function
    stores its annotations as strings rather than resolved types.

    This happens in any module that uses `from __future__ import annotations`
    (all Python versions) and is the default behaviour in Python 3.14+ (PEP 649).
    Previously, the decorator compared raw `__annotations__` values against type
    objects using `is`, which always failed for string annotations and could raise
    a `NameError` when Python's machinery tried to resolve the strings.
    """

    def test_files_attached_with_string_annotations(self, fake_files_path: Path):
        """Files manager is attached correctly when annotations are strings."""
        cli = make_string_annotated_cli()

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )

    def test_manager_parameter_injected_with_string_annotations(self, fake_files_path: Path):
        """FilesManager parameter is injected correctly when annotations are strings."""
        cli = make_string_annotated_manager_cli()

        match_output(
            cli,
            expected_pattern=["Passed"],
            exit_code=0,
            prog_name="test",
        )
