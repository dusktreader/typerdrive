from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class DatabaseError(TyperdriveError):
    exit_code: ExitCode = ExitCode.GENERAL_ERROR


class DatabaseInitError(DatabaseError):
    pass


class DatabaseQueryError(DatabaseError):
    pass


class DatabaseTransactionError(DatabaseError):
    pass


class DatabaseRollbackError(DatabaseError):
    pass


class DatabaseMigrationError(DatabaseError):
    pass


class DatabaseMigrationIntegrityError(DatabaseMigrationError):
    pass


class DatabaseLifecycleError(DatabaseError):
    pass


class DatabaseManagementError(DatabaseError):
    pass
