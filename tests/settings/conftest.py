from collections.abc import Generator
from pathlib import Path

import pytest

from typerdrive.env import tweak_env


@pytest.fixture
def fake_settings_path(tmp_path: Path) -> Generator[Path, None, None]:
    fake_settings_dir = tmp_path / ".local/share/test"
    fake_settings_dir.mkdir(parents=True)
    settings_path = fake_settings_dir / "settings.json"

    with tweak_env(HOME=str(tmp_path)):
        yield settings_path
