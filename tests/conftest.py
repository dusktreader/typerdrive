import pytest
from typer.testing import CliRunner
from typerdrive.config import set_typerdrive_config


@pytest.fixture(scope="session", autouse=True)
def _():
    set_typerdrive_config(app_name="test")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
