from typing import TYPE_CHECKING, Any

from typerdrive.database.exceptions import (
    DatabaseError,
    DatabaseInitError,
    DatabaseLifecycleError,
    DatabaseManagementError,
    DatabaseMigrationError,
    DatabaseMigrationIntegrityError,
    DatabaseQueryError,
    DatabaseRollbackError,
    DatabaseTransactionError,
)
from typerdrive.database.commands import add_database_subcommand
from typerdrive.database.manager import DatabaseManager
from typerdrive.database.migrations import Migration, MigrationRegistry

if TYPE_CHECKING:
    from typerdrive.database.attach import attach_database, get_database_manager


def __getattr__(name: str) -> Any:
    if name in {"attach_database", "get_database_manager"}:
        from typerdrive.database.attach import attach_database, get_database_manager

        return {"attach_database": attach_database, "get_database_manager": get_database_manager}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DatabaseError",
    "DatabaseInitError",
    "DatabaseLifecycleError",
    "DatabaseManagementError",
    "DatabaseManager",
    "DatabaseMigrationError",
    "DatabaseMigrationIntegrityError",
    "DatabaseQueryError",
    "DatabaseRollbackError",
    "DatabaseTransactionError",
    "Migration",
    "MigrationRegistry",
    "add_database_subcommand",
    "attach_database",
    "get_database_manager",
]
