import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from typerdrive.files.exceptions import FilesError, FilesInitError
from typerdrive.files.manager import FilesManager


class TestFilesManager:
    def test_init__no_issues(self, fake_files_path: Path):
        manager = FilesManager()
        assert manager.files_dir == fake_files_path

    def test_init__raises_exception_on_fail(self, mocker: MockerFixture):
        mocker.patch("typerdrive.files.manager.Path.mkdir", side_effect=RuntimeError("BOOM!"))
        with pytest.raises(FilesInitError, match="Failed to initialize files storage"):
            FilesManager()

    def test_resolve_path__basic(self, fake_files_path: Path):
        test_path = Path("documents/report.txt")
        manager = FilesManager()
        full_path = manager.resolve_path(test_path)
        assert full_path == fake_files_path / test_path

    def test_resolve_path__fails_if_path_is_outside_files(self, fake_files_path: Path):
        test_path = Path("../documents")
        manager = FilesManager()
        full_path = fake_files_path / test_path
        with pytest.raises(
            FilesError, match=f"Resolved file path .* is not within files directory {str(fake_files_path)}"
        ):
            manager.resolve_path(full_path)

    def test_resolve_path__fails_if_path_is_the_same_as_files_path(self, fake_files_path: Path):
        test_path = Path(".")
        manager = FilesManager()
        full_path = fake_files_path / test_path
        with pytest.raises(
            FilesError,
            match=f"Resolved file path .* must not be the same as files directory {str(fake_files_path)}",
        ):
            manager.resolve_path(full_path)

    def test_resolve_path__makes_parents_if_requested(self, fake_files_path: Path):
        test_path = Path("documents/reports/2024.txt")
        manager = FilesManager()
        full_path = manager.resolve_path(test_path, mkdir=True)
        assert full_path == fake_files_path / test_path
        assert full_path.parent.exists()

    def test_resolve_path__works_with_strings(self, fake_files_path: Path):
        test_path = "documents/report.txt"
        manager = FilesManager()
        full_path = manager.resolve_path(test_path)
        assert full_path == fake_files_path / test_path

    def test_list_items__basic(self, fake_files_path: Path):
        test_path = fake_files_path / "documents"
        test_path.mkdir()
        names = ["report.txt", "memo.txt", "invoice.pdf"]
        for name in names:
            (test_path / name).touch()
        manager = FilesManager()
        assert sorted(manager.list_items("documents")) == sorted(names)

    def test_list_items__raises_error_if_path_does_not_exist(self):
        manager = FilesManager()
        with pytest.raises(FilesError, match="Resolved file path .* does not exist"):
            manager.list_items("documents")

    def test_list_items__raises_error_if_path_is_not_a_directory(self, fake_files_path: Path):
        (fake_files_path / "document.txt").touch()
        manager = FilesManager()
        with pytest.raises(FilesError, match="Resolved file path .* is not a directory"):
            manager.list_items("document.txt")

    def test_store_bytes__basic(self, fake_files_path: Path):
        test_path = Path("documents/report.txt")
        manager = FilesManager()
        data = b"test data"
        manager.store_bytes(data, test_path)
        full_path = fake_files_path / test_path
        assert full_path.read_bytes() == data

    def test_store_bytes__raises_error_if_write_fails(self, fake_files_path: Path, mocker: MockerFixture):
        mocker.patch("typerdrive.files.manager.Path.write_bytes", side_effect=RuntimeError("BOOM!"))
        test_path = Path("documents/report.txt")
        manager = FilesManager()
        data = b"test data"
        with pytest.raises(FilesError, match="Failed to store file at documents/report.txt"):
            manager.store_bytes(data, test_path)
        full_path = fake_files_path / test_path
        assert not full_path.exists()

    def test_store_bytes__sets_mode(self, fake_files_path: Path):
        test_path = Path("documents/script.sh")
        manager = FilesManager()
        data = b"#!/bin/bash\necho test"
        mode = 0o755
        manager.store_bytes(data, test_path, mode=mode)
        full_path = fake_files_path / test_path
        assert full_path.stat().st_mode & 0o777 == mode

    def test_store_bytes__raises_error_if_chmod_fails(self, fake_files_path: Path, mocker: MockerFixture):
        mocker.patch("typerdrive.files.manager.Path.chmod", side_effect=RuntimeError("BOOM!"))
        test_path = Path("documents/script.sh")
        manager = FilesManager()
        data = b"#!/bin/bash\necho test"
        mode = 0o755
        with pytest.raises(FilesError, match=f"Failed to set mode for file at documents/script.sh to {mode=}"):
            manager.store_bytes(data, test_path, mode=mode)
        full_path = fake_files_path / test_path
        assert full_path.stat().st_mode & 0o777 != mode

    def test_store_text__basic(self, fake_files_path: Path):
        test_path = Path("documents/memo.txt")
        manager = FilesManager()
        data = "Important memo content"
        manager.store_text(data, test_path)
        full_path = fake_files_path / test_path
        assert full_path.read_text() == data

    def test_store_json__basic(self, fake_files_path: Path):
        test_path = Path("config/settings.json")
        manager = FilesManager()
        data = dict(name="myapp", version="1.0.0")
        manager.store_json(data, test_path)
        full_path = fake_files_path / test_path
        assert json.loads(full_path.read_text()) == data

    def test_load_bytes__basic(self, fake_files_path: Path):
        test_path = Path("documents/data.bin")
        manager = FilesManager()
        data = b"binary data"
        full_path = fake_files_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        loaded_data = manager.load_bytes(test_path)
        assert loaded_data == data

    def test_load_bytes__raises_error_if_file_does_not_exist(self):
        test_path = Path("documents/missing.txt")
        manager = FilesManager()
        with pytest.raises(FilesError, match="File at documents/missing.txt does not exist"):
            manager.load_bytes(test_path)

    def test_load_bytes__fails_if_read_fails(self, fake_files_path: Path, mocker: MockerFixture):
        mocker.patch("typerdrive.files.manager.Path.read_bytes", side_effect=RuntimeError("BOOM!"))
        test_path = Path("documents/data.bin")
        manager = FilesManager()
        data = b"binary data"
        full_path = fake_files_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        with pytest.raises(FilesError, match="Failed to load file from documents/data.bin"):
            manager.load_bytes(test_path)

    def test_load_text__basic(self, fake_files_path: Path):
        test_path = Path("documents/note.txt")
        manager = FilesManager()
        data = "Note contents"
        full_path = fake_files_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data.encode("utf-8"))
        loaded_data = manager.load_text(test_path)
        assert loaded_data == data

    def test_load_json__basic(self, fake_files_path: Path):
        test_path = Path("config/app.json")
        manager = FilesManager()
        data = dict(debug=True, timeout=30)
        full_path = fake_files_path / test_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(json.dumps(data).encode("utf-8"))
        loaded_data = manager.load_json(test_path)
        assert loaded_data == data

    def test_delete__basic(self, fake_files_path: Path):
        test_path = Path("documents/temp.txt")
        other_path = Path("documents/keep.txt")
        manager = FilesManager()
        data = b"temp data"
        other_data = b"keep this"
        manager.store_bytes(data, test_path)
        manager.store_bytes(other_data, other_path)
        full_path = manager.delete(test_path)
        assert full_path == fake_files_path / test_path
        assert not full_path.exists()

        other_full_path = fake_files_path / other_path
        assert other_full_path.read_bytes() == other_data

    def test_delete__raises_error_if_unlink_fails(self, mocker: MockerFixture):
        mocker.patch("typerdrive.files.manager.Path.unlink", side_effect=RuntimeError("BOOM!"))
        test_path = Path("documents/file.txt")
        manager = FilesManager()
        with pytest.raises(FilesError, match="Failed to delete file at documents/file.txt"):
            manager.delete(test_path)
