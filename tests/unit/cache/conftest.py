from collections.abc import Generator
from pathlib import Path

import pytest
from typerdrive.env import tweak_env


@pytest.fixture
def fake_cache_path(tmp_path: Path) -> Generator[Path, None, None]:
    fake_cache_home = tmp_path / ".cache"
    fake_path = fake_cache_home / "test"
    fake_path.mkdir(parents=True)

    with tweak_env(HOME=str(tmp_path), XDG_CACHE_HOME=str(fake_cache_home)):
        yield fake_path
