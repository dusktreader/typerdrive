"""
Provide a class for managing the `typerdrive` logging feature.
"""

import sys
from pathlib import Path
from typing import Any

from loguru import logger
from rich.console import Console

from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.dirs import clear_directory, show_directory


class LoggingManager:
    """
    Manage logs for the `typerdrive` app.
    """

    log_dir: Path
    """ The directory where the logs are stored. """

    log_file: Path
    """ The filename for the log file. """

    def __init__(self, *, verbose: bool = False):
        config: TyperdriveConfig = get_typerdrive_config()

        self.log_dir = config.log_dir
        self.log_file = config.log_dir / config.log_file_name

        handlers: list[dict[str, Any]] = [
            dict(
                sink=str(self.log_file),
                level="DEBUG",
                rotation=config.log_file_rotation,
                retention=config.log_file_retention,
                compression=config.log_file_compression,
            ),
        ]
        if verbose:
            handlers.append(
                dict(
                    sink=sys.stdout,
                    level="DEBUG",
                    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>"
                ),
            )

        # Having a hell of a time getting the typing right for `configure()`
        logger.configure(handlers=handlers)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        logger.enable("typerdrive")

    def show(self):
        """
        Show the current log file.
        """
        console = Console()
        with console.pager(styles=True):
            console.print(self.log_file.read_text())

    def audit(self):
        """
        Show the directory containing the log files.
        """
        show_directory(self.log_dir, subject="Current log files")

    def clear(self):
        """
        Remove all log files.
        """
        clear_directory(self.log_dir)
