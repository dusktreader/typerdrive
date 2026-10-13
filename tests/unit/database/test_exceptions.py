import pytest

from typerdrive.constants import ExitCode
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
from typerdrive.exceptions import TyperdriveError


@pytest.mark.parametrize(
    "error_type",
    [
        DatabaseError,
        DatabaseInitError,
        DatabaseLifecycleError,
        DatabaseManagementError,
        DatabaseMigrationError,
        DatabaseMigrationIntegrityError,
        DatabaseQueryError,
        DatabaseRollbackError,
        DatabaseTransactionError,
    ],
)
def test_database_errors_derive_from_typerdrive_error(error_type):
    error = error_type("database failure")

    assert isinstance(error, TyperdriveError)
    assert str(error) == "database failure"
    assert error.exit_code == ExitCode.GENERAL_ERROR
