from importlib.metadata import PackageNotFoundError
from unittest import mock

from typerdrive.version import (
    __version__,
    get_version,
    get_version_from_metadata,
    get_version_from_pyproject,
)


def test_get_version_from_metadata():
    assert get_version_from_metadata() == __version__


def test_get_version_from_pyproject():
    assert get_version_from_pyproject() == __version__


def test_get_version__uses_pyproject():
    expected_version = "1.2.3"
    with mock.patch(
        "typerdrive.version.get_version_from_metadata", side_effect=PackageNotFoundError
    ) as mocked_metadata:
        with mock.patch(
            "typerdrive.version.get_version_from_pyproject", return_value=expected_version
        ) as mocked_pyproject:
            computed_version = get_version()
            assert computed_version == expected_version

            mocked_metadata.assert_called_once()
            mocked_pyproject.assert_called_once()


def test_get_version__uses_metadata():
    expected_version = "1.2.3"
    with mock.patch("typerdrive.version.get_version_from_metadata", return_value=expected_version) as mocked_metadata:
        with mock.patch(
            "typerdrive.version.get_version_from_pyproject", side_effect=FileNotFoundError
        ) as mocked_pyproject:
            computed_version = get_version()
            assert computed_version == expected_version

            mocked_metadata.assert_called_once()
            mocked_pyproject.assert_not_called()


def test_get_version__returns_unknown_if_both_fail():
    expected_version = "unknown"
    with mock.patch(
        "typerdrive.version.get_version_from_metadata", side_effect=PackageNotFoundError
    ) as mocked_metadata:
        with mock.patch(
            "typerdrive.version.get_version_from_pyproject", side_effect=FileNotFoundError
        ) as mocked_pyproject:
            computed_version = get_version()
            assert computed_version == expected_version

            mocked_metadata.assert_called_once()
            mocked_pyproject.assert_called_once()
