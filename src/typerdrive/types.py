import datetime
from collections.abc import Callable
from typing import TextIO

# The types accepted align with loguru file sink rotation and retention spec.
# See: https://github.com/Delgan/loguru/blob/a69bfc451413f71b81761a238db4b5833cf0a992/loguru/__init__.pyi#L139
# See: https://loguru.readthedocs.io/en/stable/api/logger.html#file
FileRotationSpec = str | int | datetime.timedelta | datetime.time | Callable[[str, TextIO], bool]
FileRetentionSpec = str | int | datetime.timedelta | Callable[[list[str]], None]
FileCompressionSpec = str | Callable[[str], None]
