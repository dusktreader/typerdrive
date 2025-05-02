from pathlib import Path
from collections.abc import Generator

import pytest

from typerdrive.env import tweak_env


@pytest.fixture
def fake_cache_path(tmp_path: Path) -> Generator[Path, None, None]:
    fake_path = tmp_path / ".cache/test"
    fake_path.mkdir(parents=True)

    with tweak_env(HOME=str(tmp_path)):
        yield fake_path
