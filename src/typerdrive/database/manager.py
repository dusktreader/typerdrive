from pathlib import Path

from typerdrive.config import get_typerdrive_config
from typerdrive.database.exceptions import DatabaseInitError
from typerdrive.database.session import DatabaseSession


class DatabaseManager:
    def __init__(self, database_path: Path | str | None = None, journal_mode: str = "WAL"):
        self.database_path = Path(database_path) if database_path is not None else get_typerdrive_config().database_path
        self.journal_mode = journal_mode.upper()
        if self.journal_mode not in {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}:
            raise DatabaseInitError(f"Unsupported SQLite journal mode: {journal_mode}")

    def create_session(self) -> DatabaseSession:
        return DatabaseSession(self.database_path, self.journal_mode)
