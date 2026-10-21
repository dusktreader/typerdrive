from collections.abc import Generator
from pathlib import Path

import pytest
from typerdrive.config import get_typerdrive_config, set_typerdrive_config
from typerdrive.env import tweak_env


@pytest.fixture
def fake_cache_path(tmp_path: Path) -> Generator[Path, None, None]:
    state_home = tmp_path / ".local/state"
    cache_home = tmp_path / ".cache"
    fake_path = cache_home / "test"
    fake_path.mkdir(parents=True)
    original_config = get_typerdrive_config()

    with tweak_env(HOME=str(tmp_path), XDG_STATE_HOME=str(state_home), XDG_CACHE_HOME=str(cache_home)):
        set_typerdrive_config(state_home=state_home, cache_home=cache_home)
        try:
            yield fake_path
        finally:
            set_typerdrive_config(**original_config.model_dump())
