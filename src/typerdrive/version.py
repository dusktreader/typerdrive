"""
Provide methods for getting the project version.
"""

import tomllib
from importlib import metadata


def get_version_from_metadata() -> str:
    """
    Retrieve version from package metadata.
    """
    return metadata.version(__package__ or __name__)


def get_version_from_pyproject() -> str:
    """
    Retrieve version from the `pyproject.toml` file.
    """
    with open("pyproject.toml", "rb") as file:
        return tomllib.load(file)["project"]["version"]


def get_version() -> str:
    """
    Try to get version from metadata, then fallback to `pyproject.toml`, then fallback to "unknown".
    """
    try:
        return get_version_from_metadata()
    except metadata.PackageNotFoundError:
        try:
            return get_version_from_pyproject()
        except (FileNotFoundError, KeyError):
            return "unknown"


__version__ = get_version()
