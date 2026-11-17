from pathlib import Path
from typing import cast

import pytest
from typerdrive.file_ops import atomic_write


def test_atomic_write_create_only_does_not_overwrite(tmp_path: Path):
    path = tmp_path / "data"
    path.write_bytes(b"old")

    with pytest.raises(FileExistsError):
        atomic_write(path, b"new", create_only=True)

    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_write_uses_private_file_mode(tmp_path: Path):
    path = tmp_path / "data"

    atomic_write(path, b"secret")

    assert path.stat().st_mode & 0o777 == 0o600


def test_atomic_write_cleans_temporary_file_after_write_error(tmp_path: Path):
    path = tmp_path / "data"
    path.write_bytes(b"old")

    with pytest.raises(TypeError):
        atomic_write(path, cast(bytes, "not bytes"))

    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_write_cleans_temporary_file_after_replace_error(tmp_path: Path):
    path = tmp_path / "data"
    path.mkdir()

    with pytest.raises(OSError):
        atomic_write(path, b"new")

    assert path.is_dir()
    assert list(tmp_path.iterdir()) == [path]
