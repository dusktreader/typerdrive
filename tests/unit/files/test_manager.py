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
            FilesError, match=f"Resolved file path .* is not within files directory {fake_files_path!s}"
        ):
            manager.resolve_path(full_path)

    def test_resolve_path__fails_if_path_is_the_same_as_files_path(self, fake_files_path: Path):
        test_path = Path(".")
        manager = FilesManager()
        full_path = fake_files_path / test_path
        with pytest.raises(
            FilesError,
            match=f"Resolved file path .* must not be the same as files directory {fake_files_path!s}",
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

    @pytest.mark.parametrize("target_kind", ["file", "directory", "broken"])
    def test_resolve_path__rejects_symlink_components(self, fake_files_path: Path, target_kind: str):
        target = fake_files_path / "target"
        if target_kind == "directory":
            target.mkdir()
        elif target_kind == "file":
            target.touch()
        (fake_files_path / "link").symlink_to(target)
        if target_kind == "broken":
            (fake_files_path / "link").unlink()
            (fake_files_path / "link").symlink_to(fake_files_path / "missing")

        manager = FilesManager()
        with pytest.raises(FilesError, match="symlink"):
            manager.resolve_path("link/child" if target_kind == "directory" else "link")

    @pytest.mark.parametrize("target_kind", ["internal", "external", "broken"])
    @pytest.mark.parametrize("operation", ["store", "load", "delete", "list"])
    def test_file_operations__reject_symlink_paths(
        self, fake_files_path: Path, tmp_path: Path, target_kind: str, operation: str
    ):
        external = tmp_path / "external.txt"
        external.write_bytes(b"outside")
        target = fake_files_path / "target.txt" if target_kind == "internal" else external
        if target_kind == "internal":
            target.write_bytes(b"inside")
        elif target_kind == "broken":
            target = fake_files_path / "missing.txt"
        expected_target_contents = target.read_bytes() if target.exists() else None
        link = fake_files_path / "link"
        link.symlink_to(target)
        manager = FilesManager()

        with pytest.raises(FilesError, match="symlink"):
            if operation == "store":
                manager.store_bytes(b"changed", "link")
            elif operation == "load":
                manager.load_bytes("link")
            elif operation == "delete":
                manager.delete("link")
            else:
                manager.list_items("link")

        assert target.exists() == (expected_target_contents is not None)
        if expected_target_contents is not None:
            assert target.read_bytes() == expected_target_contents
        assert link.is_symlink()

    def test_resolve_path__supports_symlinked_configured_root(self, fake_files_path: Path, tmp_path: Path):
        root_link = tmp_path / "files-link"
        root_link.symlink_to(fake_files_path, target_is_directory=True)
        manager = FilesManager()
        manager.files_dir = root_link

        path = manager.resolve_path("document.txt")
        manager.store_text("contents", "document.txt")

        assert path == fake_files_path / "document.txt"
        assert manager.load_text("document.txt") == "contents"

    def test_list_items__default_is_immediate_only(self, fake_files_path: Path):
        (fake_files_path / "documents/nested").mkdir(parents=True)
        (fake_files_path / "documents/root.txt").touch()
        (fake_files_path / "documents/nested/child.txt").touch()
        manager = FilesManager()

        assert manager.list_items("documents") == ["root.txt"]

    def test_list_items__recursive_returns_storage_root_relative_keys(self, fake_files_path: Path):
        (fake_files_path / "documents/nested/deep").mkdir(parents=True)
        (fake_files_path / "documents/root.txt").touch()
        (fake_files_path / "documents/nested/child.txt").touch()
        (fake_files_path / "documents/nested/deep/grandchild.txt").touch()
        manager = FilesManager()

        keys = manager.list_items("documents", recursive=True)

        assert set(keys) == {
            "documents/root.txt",
            "documents/nested/child.txt",
            "documents/nested/deep/grandchild.txt",
        }
        for key in keys:
            assert manager.resolve_path(key).is_file()
        assert set(manager.list_items("documents/nested", recursive=True)) == {
            "documents/nested/child.txt",
            "documents/nested/deep/grandchild.txt",
        }

    def test_list_items__pattern_matches_from_requested_directory(self, fake_files_path: Path):
        (fake_files_path / "documents/nested/deep").mkdir(parents=True)
        (fake_files_path / "documents/root.md.j2").touch()
        (fake_files_path / "documents/nested/nested.md.j2").touch()
        (fake_files_path / "documents/nested/deep/deep.md.j2").touch()
        (fake_files_path / "documents/root.yaml").touch()
        manager = FilesManager()

        assert set(manager.list_items("documents", recursive=True, pattern="*.md.j2")) == {
            "documents/root.md.j2"
        }
        assert set(manager.list_items("documents", recursive=True, pattern="**/*.md.j2")) == {
            "documents/root.md.j2",
            "documents/nested/nested.md.j2",
            "documents/nested/deep/deep.md.j2",
        }
        assert manager.list_items("documents", pattern="**/*.md.j2") == ["root.md.j2"]

    def test_list_items__pattern_preserves_missing_and_symlink_behavior(
        self, fake_files_path: Path, tmp_path: Path
    ):
        (fake_files_path / "documents").mkdir()
        (fake_files_path / "documents/visible.txt").touch()
        (fake_files_path / "documents/linked.txt").symlink_to(fake_files_path / "documents/visible.txt")
        external = tmp_path / "external"
        external.mkdir()
        (external / "hidden.txt").touch()
        (fake_files_path / "documents/linked-dir").symlink_to(external, target_is_directory=True)
        manager = FilesManager()

        assert manager.list_items("missing", pattern="**/*.txt", missing_ok=True) == []
        with pytest.raises(FilesError, match="does not exist"):
            manager.list_items("missing", pattern="**/*.txt")
        assert manager.list_items("documents", recursive=True, pattern="**/*.txt") == ["documents/visible.txt"]

    @pytest.mark.parametrize("recursive", [False, True])
    def test_list_items__missing_ok(self, recursive: bool):
        manager = FilesManager()

        assert manager.list_items("missing", recursive=recursive, missing_ok=True) == []

    @pytest.mark.parametrize("symlink_kind", ["broken", "intermediate"])
    def test_list_items__missing_ok_rejects_symlink_paths(self, fake_files_path: Path, symlink_kind: str):
        if symlink_kind == "broken":
            (fake_files_path / "broken").symlink_to(fake_files_path / "missing")
            path = "broken"
        else:
            (fake_files_path / "target").mkdir()
            (fake_files_path / "link").symlink_to(fake_files_path / "target", target_is_directory=True)
            path = "link/missing"
        manager = FilesManager()

        with pytest.raises(FilesError, match="symlink"):
            manager.list_items(path, missing_ok=True)

    @pytest.mark.parametrize("recursive", [False, True])
    def test_list_items__root_aliases_are_rejected_through_symlinked_root(
        self, fake_files_path: Path, tmp_path: Path, recursive: bool
    ):
        (fake_files_path / "subdirectory").mkdir()
        root_link = tmp_path / "files-link"
        root_link.symlink_to(fake_files_path, target_is_directory=True)
        manager = FilesManager()
        manager.files_dir = root_link

        for path in [".", "subdirectory/..", root_link, fake_files_path.resolve()]:
            with pytest.raises(FilesError):
                manager.list_items(path, recursive=recursive, missing_ok=True)

    @pytest.mark.parametrize("recursive", [False, True])
    def test_list_items__root_aliases_are_rejected(self, fake_files_path: Path, recursive: bool):
        (fake_files_path / "subdirectory").mkdir()
        manager = FilesManager()

        for path in [".", "subdirectory/..", fake_files_path, fake_files_path.resolve()]:
            with pytest.raises(FilesError):
                manager.list_items(path, recursive=recursive, missing_ok=True)

    def test_list_items__non_directory_is_rejected_with_missing_ok(self, fake_files_path: Path):
        (fake_files_path / "document.txt").touch()
        manager = FilesManager()

        with pytest.raises(FilesError, match="is not a directory"):
            manager.list_items("document.txt", missing_ok=True)

    def test_list_items__omits_symlink_entries_and_does_not_follow_directories(
        self, fake_files_path: Path, tmp_path: Path
    ):
        (fake_files_path / "nested").mkdir()
        (fake_files_path / "nested/visible.txt").touch()
        external = tmp_path / "external"
        external.mkdir()
        (external / "hidden.txt").touch()
        (fake_files_path / "nested/linked.txt").symlink_to(fake_files_path / "nested/visible.txt")
        (fake_files_path / "nested/linked-dir").symlink_to(external, target_is_directory=True)
        manager = FilesManager()

        assert set(manager.list_items("nested", recursive=True)) == {"nested/visible.txt"}
        assert set(manager.list_items("nested")) == {"visible.txt"}

    def test_list_items__requested_read_failure_is_wrapped_with_cause(
        self, fake_files_path: Path, mocker: MockerFixture
    ):
        (fake_files_path / "documents").mkdir()
        original_iterdir = Path.iterdir
        failure = PermissionError("denied")

        def fail_requested(path: Path):
            if path == fake_files_path / "documents":
                raise failure
            return original_iterdir(path)

        mocker.patch("typerdrive.files.manager.Path.iterdir", fail_requested)
        manager = FilesManager()

        with pytest.raises(FilesError) as error:
            manager.list_items("documents", missing_ok=True)

        assert error.value.__cause__ is failure

    def test_list_items__nested_read_failure_returns_no_partial_results(
        self, fake_files_path: Path, mocker: MockerFixture
    ):
        (fake_files_path / "documents/nested").mkdir(parents=True)
        (fake_files_path / "documents/visible.txt").touch()
        original_iterdir = Path.iterdir
        failure = PermissionError("denied")

        def fail_nested(path: Path):
            if path == fake_files_path / "documents/nested":
                raise failure
            return original_iterdir(path)

        mocker.patch("typerdrive.files.manager.Path.iterdir", fail_nested)
        manager = FilesManager()

        with pytest.raises(FilesError) as error:
            manager.list_items("documents", recursive=True)

        assert error.value.__cause__ is failure

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
        data = {"name": "myapp", "version": "1.0.0"}
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
        data = {"debug": True, "timeout": 30}
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

    def test_delete__removes_empty_parent_and_preserves_storage_root(self, fake_files_path: Path):
        test_path = Path("documents/report.txt")
        manager = FilesManager()
        manager.store_bytes(b"report", test_path)

        full_path = manager.delete(test_path)

        assert full_path == fake_files_path / test_path
        assert not full_path.exists()
        assert not full_path.parent.exists()
        assert fake_files_path.is_dir()

    def test_delete__raises_error_if_unlink_fails(self, mocker: MockerFixture):
        mocker.patch("typerdrive.files.manager.Path.unlink", side_effect=RuntimeError("BOOM!"))
        test_path = Path("documents/file.txt")
        manager = FilesManager()
        with pytest.raises(FilesError, match="Failed to delete file at documents/file.txt"):
            manager.delete(test_path)
