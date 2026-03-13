"""
Shared fixtures for the typerdrive integration (BDD) tests.

Each scenario gets its own temporary HOME directory so file-system state
(settings file, cache dir, files dir) never leaks between scenarios.
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from typerdrive.config import set_typerdrive_config
from typerdrive.env import tweak_env


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner(mix_stderr=True)


@pytest.fixture
def tmp_home(tmp_path: Path) -> Generator[Path, None, None]:
    """A temporary HOME directory, isolated per-test."""
    with tweak_env(HOME=str(tmp_path)):
        yield tmp_path


@pytest.fixture(autouse=True)
def _configure_typerdrive(tmp_home: Path):  # noqa: ARG001
    """
    Reset typerdrive config to use 'test' as the app name for every integration
    scenario, pointing at the temporary HOME.
    """
    set_typerdrive_config(app_name="test", console_width=80)
