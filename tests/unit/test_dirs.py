from pathlib import Path

import pytest
from typerdrive.dirs import clear_directory
from typerdrive.exceptions import TyperdriveError


class TestHelpers:
    def test_clear_directory__basic(self, tmp_path: Path):
        tmp_path.joinpath("jawa/ewok").mkdir(parents=True)
        tmp_path.joinpath("jawa/ewok/talz").touch()

        tmp_path.joinpath("pyke/hutt").mkdir(parents=True)
        tmp_path.joinpath("pyke/hutt/muun").touch()

        tmp_path.joinpath("bith").mkdir(parents=True)
        tmp_path.joinpath("bith/gran").touch()

        tmp_path.joinpath("teek").touch()

        assert len([p for p in tmp_path.iterdir()]) == 4
        clear_directory(tmp_path)
        assert len([p for p in tmp_path.iterdir()]) == 0

    def test_clear_directory__raises_error_if_path_does_not_exist(self):
        with pytest.raises(TyperdriveError, match="Target path=.* does not exist"):
            clear_directory(Path("nonexistent"))

    def test_clear_directory__raises_error_if_path_is_not_a_directory(self, tmp_path: Path):
        nondir = tmp_path / "nondir"
        nondir.touch()
        with pytest.raises(TyperdriveError, match="Target path=.* is not a directory"):
            clear_directory(nondir)
