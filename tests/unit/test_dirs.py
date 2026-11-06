from pathlib import Path

import pytest
from typerdrive.dirs import clear_directory, show_directory
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

    def test_clear_directory__unlinks_nested_symlinks_without_touching_targets(self, tmp_path: Path):
        target_dir = tmp_path / "external"
        target_dir.mkdir()
        target_file = tmp_path / "external.txt"
        target_file.write_text("unchanged")
        nested_target = target_dir / "nested.txt"
        nested_target.write_text("also unchanged")
        directory = tmp_path / "store"
        nested = directory / "nested"
        nested.mkdir(parents=True)
        (directory / "file-link").symlink_to(target_file)
        (directory / "directory-link").symlink_to(target_dir, target_is_directory=True)
        (nested / "file-link").symlink_to(target_file)
        dangling_link = nested / "dangling-link"
        dangling_link.symlink_to(tmp_path / "missing")

        count = clear_directory(directory)

        assert count == 4
        assert list(directory.iterdir()) == []
        assert target_file.read_text() == "unchanged"
        assert nested_target.read_text() == "also unchanged"
        assert not dangling_link.exists()
        assert not dangling_link.is_symlink()

    def test_clear_directory__unlinks_directory_cycles(self, tmp_path: Path):
        directory = tmp_path / "store"
        nested = directory / "nested"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("contents")
        (nested / "cycle").symlink_to(directory, target_is_directory=True)

        count = clear_directory(directory)

        assert count == 2
        assert list(directory.iterdir()) == []

    def test_clear_directory__follows_symlinked_root_without_following_nested_links(self, tmp_path: Path):
        target = tmp_path / "target"
        target.mkdir()
        target_file = target / "file.txt"
        target_file.write_text("remove this")
        external_file = tmp_path / "external.txt"
        external_file.write_text("leave this unchanged")
        (target / "nested-link").symlink_to(external_file)
        link = tmp_path / "directory-link"
        link.symlink_to(target, target_is_directory=True)

        count = clear_directory(link)

        assert count == 2
        assert link.is_symlink()
        assert list(target.iterdir()) == []
        assert external_file.read_text() == "leave this unchanged"

    def test_show_directory__omits_symlink_display(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        directory = tmp_path / "directory"
        directory.mkdir()
        root_file = directory / "root.txt"
        root_file.write_text("Stay")
        external_dir = tmp_path / "external"
        external_dir.mkdir()
        (external_dir / "nested.txt").write_text("hidden")
        (directory / "linked.txt").symlink_to(root_file)
        (directory / "linked-dir").symlink_to(external_dir, target_is_directory=True)

        show_directory(directory)

        output = capsys.readouterr().out
        assert "root.txt" in output
        assert "linked.txt" not in output
        assert "linked-dir" not in output
        assert "nested.txt" not in output
        assert "Storing 4 Bytes in 1 files" in output
