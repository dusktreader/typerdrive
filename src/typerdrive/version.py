import tomllib
from importlib import metadata


def get_version_from_metadata() -> str:
    return metadata.version(__package__ or __name__)


def get_version_from_pyproject() -> str:
    with open("pyproject.toml", "rb") as file:
        return tomllib.load(file)["project"]["version"]


def get_version() -> str:
    try:
        return get_version_from_metadata()
    except metadata.PackageNotFoundError:
        try:
            return get_version_from_pyproject()
        except (FileNotFoundError, KeyError):
            return "unknown"


__version__ = get_version()
