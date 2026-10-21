from collections.abc import Generator
from pathlib import Path

import pytest
from typerdrive.config import get_typerdrive_config, set_typerdrive_config
from typerdrive.env import tweak_env


@pytest.fixture(autouse=True)
def fake_settings_path(tmp_path: Path) -> Generator[Path, None, None]:
    state_home = tmp_path / ".local/state"
    cache_home = tmp_path / ".cache"
    settings_dir = state_home / "test"
    settings_dir.mkdir(parents=True)
    settings_path = settings_dir / "settings.json"
    original_config = get_typerdrive_config()

    with tweak_env(HOME=str(tmp_path), XDG_STATE_HOME=str(state_home), XDG_CACHE_HOME=str(cache_home)):
        set_typerdrive_config(state_home=state_home, cache_home=cache_home)
        try:
            yield settings_path
        finally:
            set_typerdrive_config(**original_config.model_dump())
