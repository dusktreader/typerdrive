"""
Provide a class for managing the `typerdrive` logging feature.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

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
        logger.configure(handlers=handlers)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        logger.enable("typerdrive")

    def show(self, *, follow: bool = False, lines: Optional[int] = None):
        """
        Show the current log file.
        """
        if follow:
            cmd = ["tail", "-f"]
            if lines is not None:
                cmd += ["-n", str(lines)]
            cmd.append(str(self.log_file))
            subprocess.run(cmd)
        else:
            text = self.log_file.read_text()
            if lines is not None:
                text = "\n".join(text.splitlines()[-lines:])
            console = Console()
            with console.pager(styles=True):
                console.print(text, markup=False)

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
