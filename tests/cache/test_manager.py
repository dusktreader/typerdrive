import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from snick import dedent

from typerdrive.cache.exceptions import CacheError, CacheInitError
from typerdrive.cache.manager import CacheManager, clear_directory

from tests.cache.helpers import tree_to_text


class TestSettingsManager:
    def test_init__no_issues(self, fake_cache_path: Path):
        manager = CacheManager("test")
        assert manager.app_name == "test"
        assert manager.cache_path == fake_cache_path

    def test_init__raises_exception_on_fail(self, mocker: MockerFixture):
        mocker.patch("typerdrive.cache.manager.Path.mkdir", side_effect=RuntimeError("BOOM!"))
        with pytest.raises(CacheInitError, match="Failed to initialize cache"):
            CacheManager("test")

    def test_resolve_path__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        full_path = manager.resolve_path(test_path)
        assert full_path == fake_cache_path / test_path

    def test_resolve_path__fails_if_path_is_outside_cache(self, fake_cache_path: Path):
        test_path = Path("../jawa")
        manager = CacheManager("test")
        full_path = fake_cache_path / test_path
        with pytest.raises(CacheError, match=f"Resolved cache path .* is not within cache {str(fake_cache_path)}"):
            manager.resolve_path(full_path)

    def test_resolve_path__fails_if_path_is_the_same_as_cache_path(self, fake_cache_path: Path):
        test_path = Path(".")
        manager = CacheManager("test")
        full_path = fake_cache_path / test_path
        with pytest.raises(
            CacheError,
            match=f"Resolved cache path .* must not be the same as cache {str(fake_cache_path)}",
        ):
            manager.resolve_path(full_path)

    def test_resolve_path__makes_parents_if_requested(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        full_path = manager.resolve_path(test_path, mkdir=True)
        assert full_path == fake_cache_path / test_path
        assert full_path.parent.exists()

    def test_resolve_path__works_with_strings(self, fake_cache_path: Path):
        test_path = "jawa/ewok/hutt"
        manager = CacheManager("test")
        full_path = manager.resolve_path(test_path)
        assert full_path == fake_cache_path / test_path

    def test_store_bytes__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = b"test data"
        manager.store_bytes(data, test_path)
        full_path = fake_cache_path / test_path
        assert full_path.read_bytes() == data

    def test_store_bytes__raises_error_if_write_fails(self, fake_cache_path: Path, mocker: MockerFixture):
        mocker.patch("typerdrive.cache.manager.Path.write_bytes", side_effect=RuntimeError("BOOM!"))
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = b"test data"
        with pytest.raises(CacheError, match="Failed to store data in cache target jawa/ewok/hutt"):
            manager.store_bytes(data, test_path)
        full_path = fake_cache_path / test_path
        assert not full_path.exists()

    def test_store_bytes__sets_mode(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = b"test data"
        mode = 0o141
        manager.store_bytes(data, test_path, mode=mode)
        full_path = fake_cache_path / test_path
        assert full_path.stat().st_mode & 0o777 == mode

    def test_store_bytes__raises_error_if_chmod_fails(self, fake_cache_path: Path, mocker: MockerFixture):
        mocker.patch("typerdrive.cache.manager.Path.chmod", side_effect=RuntimeError("BOOM!"))
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = b"test data"
        mode = 0o141
        with pytest.raises(CacheError, match=f"Failed to set mode for cache target jawa/ewok/hutt to {mode=}"):
            manager.store_bytes(data, test_path, mode=mode)
        full_path = fake_cache_path / test_path
        assert full_path.stat().st_mode & 0o777 != mode

    def test_store_text__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = "test data"
        manager.store_text(data, test_path)
        full_path = fake_cache_path / test_path
        assert full_path.read_text() == data

    def test_store_json__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = dict(name="sleazy", species="hutt")
        manager.store_json(data, test_path)
        full_path = fake_cache_path / test_path
        assert json.loads(full_path.read_text()) == data

    def test_load_bytes__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = b"test data"
        full_path = fake_cache_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        loaded_data = manager.load_bytes(test_path)
        assert loaded_data == data

    def test_load_bytes__raises_error_if_file_does_not_exist(self):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        with pytest.raises(CacheError, match="Cache target jawa/ewok/hutt does not exist"):
            manager.load_bytes(test_path)

    def test_load_bytes__fails_if_read_fails(self, fake_cache_path: Path, mocker: MockerFixture):
        mocker.patch("typerdrive.cache.manager.Path.read_bytes", side_effect=RuntimeError("BOOM!"))
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = b"test data"
        full_path = fake_cache_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        with pytest.raises(CacheError, match="Failed to load data from cache target jawa/ewok/hutt"):
            manager.load_bytes(test_path)

    def test_load_text__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = "test data"
        full_path = fake_cache_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data.encode("utf-8"))
        loaded_data = manager.load_text(test_path)
        assert loaded_data == data

    def test_load_json__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        data = dict(name="sleazy", species="hutt")
        full_path = fake_cache_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(json.dumps(data).encode("utf-8"))
        loaded_data = manager.load_json(test_path)
        assert loaded_data == data

    def test_clear_path__basic(self, fake_cache_path: Path):
        test_path = Path("jawa/ewok/hutt")
        other_path = Path("jawa/ewok/pyke")
        manager = CacheManager("test")
        data = b"test data"
        other_data = b"other data"
        manager.store_bytes(data, test_path)
        manager.store_bytes(other_data, other_path)
        full_path = manager.clear_path(test_path)
        assert full_path == fake_cache_path / test_path
        assert not full_path.exists()

        other_full_path = fake_cache_path / other_path
        assert other_full_path.read_bytes() == other_data

    def test_clear_path__raises_error_if_unlink_fails(self, mocker: MockerFixture):
        mocker.patch("typerdrive.cache.manager.Path.unlink", side_effect=RuntimeError("BOOM!"))
        test_path = Path("jawa/ewok/hutt")
        manager = CacheManager("test")
        with pytest.raises(CacheError, match="Failed to clear cache target jawa/ewok/hutt"):
            manager.clear_path(test_path)

    def test_clear_all__basic(self, fake_cache_path: Path):
        manager = CacheManager("test")
        manager.store_bytes(b"jawa", "jawa")
        manager.store_bytes(b"ewok", "ewok")
        manager.store_bytes(b"hutt & pyke", "hutt/pyke")
        assert len([p for p in fake_cache_path.iterdir()]) == 3
        manager.clear_all()
        assert len([p for p in fake_cache_path.iterdir()]) == 0

    def test_clear_all__raises_error_if_clear_directory_fails(self, mocker: MockerFixture):
        mocker.patch("typerdrive.cache.manager.clear_directory", side_effect=RuntimeError("BOOM!"))
        manager = CacheManager("test")
        with pytest.raises(CacheError, match="Failed to clear cache"):
            manager.clear_all()

    def test_pretty(self, fake_cache_path: Path):
        manager = CacheManager("test")
        manager.store_bytes(b"jawa", "jawa")
        manager.store_bytes(b"ewok", "ewok")
        manager.store_bytes(b"hutt & pyke", "hutt/pyke")
        cache_info = manager.pretty()
        expected = dedent(f"""
            📂 {fake_cache_path}
            ├── 📂 hutt
            │   └── 📄 pyke (11 Bytes)
            ├── 📄 ewok (4 Bytes)
            └── 📄 jawa (4 Bytes)
        """)
        assert tree_to_text(cache_info.tree) == expected


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
        with pytest.raises(CacheError, match="Target path=.* does not exist"):
            clear_directory(Path("nonexistent"))

    def test_clear_directory__raises_error_if_path_is_not_a_directory(self, tmp_path: Path):
        nondir = tmp_path / "nondir"
        nondir.touch()
        with pytest.raises(CacheError, match="Target path=.* is not a directory"):
            clear_directory(nondir)
