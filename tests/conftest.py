from collections.abc import Generator
import pytest
from loguru import logger
from typer.testing import CliRunner

from typerdrive.config import set_typerdrive_config


@pytest.fixture(scope="session", autouse=True)
def _():
    set_typerdrive_config(
        app_name="test",
        console_width=80,
    )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def caplog(caplog: pytest.LogCaptureFixture) -> Generator[pytest.LogCaptureFixture, None, None]:
    logger.enable("typerdrive")
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)
