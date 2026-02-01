from collections.abc import Generator
from pathlib import Path

import pytest
from typerdrive.env import tweak_env


@pytest.fixture
def fake_files_path(tmp_path: Path) -> Generator[Path, None, None]:
    fake_path = tmp_path / ".local/state/test/files"
    fake_path.mkdir(parents=True)

    with tweak_env(HOME=str(tmp_path)):
        yield fake_path
