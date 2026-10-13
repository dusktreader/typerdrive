import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import inflection

from typerdrive.database.exceptions import DatabaseMigrationError, DatabaseMigrationIntegrityError
from typerdrive.database.manager import DatabaseManager


@dataclass(frozen=True)
class Migration:
    index: int
    migration_id: str
    description: str
    sql_text: str
    checksum: str


class MigrationRegistry:
    def __init__(self):
        self._migrations: list[Migration] = []

    @property
    def migrations(self) -> tuple[Migration, ...]:
        return tuple(self._migrations)

    def register_migration(self, desc: str, sql_text: str) -> Migration:
        index = len(self._migrations) + 1
        migration_id = f"{index:08d}{inflection.underscore(desc)}"
        checksum = hashlib.sha256(sql_text.encode("utf-8")).hexdigest()
        migration = Migration(index, migration_id, desc, sql_text, checksum)
        self._migrations.append(migration)
        return migration

    def validate(self) -> tuple[tuple[Migration, tuple[str, ...]], ...]:
        validated: list[tuple[Migration, tuple[str, ...]]] = []
        for migration in self._migrations:
            if not migration.description.strip():
                raise DatabaseMigrationError(f"Migration {migration.index} has an empty description")
            if not migration.sql_text.strip():
                raise DatabaseMigrationError(f"Migration {migration.index} has empty SQL text")
            validated.append((migration, self._split_sql(migration.sql_text)))
        return tuple(validated)

    async def apply(self, manager: DatabaseManager) -> None:
        migrations = self.validate()
        await manager.execute(
            "CREATE TABLE IF NOT EXISTS _typerdrive_migrations ("
            "migration_index INTEGER PRIMARY KEY, "
            "migration_id TEXT NOT NULL UNIQUE, "
            "checksum TEXT NOT NULL)"
        )
        async with manager.transaction(immediate=True):
            await self._verify_history(manager, migrations)
        for migration, statements in migrations:
            try:
                async with manager.transaction(immediate=True):
                    await self._apply_migrations_in_transaction(manager, ((migration, statements),), migrations)
            except DatabaseMigrationIntegrityError:
                raise
            except DatabaseMigrationError:
                raise
            except Exception as error:
                raise DatabaseMigrationError(
                    f"Failed to apply migration {migration.migration_id}: {error}"
                ) from error

    async def _apply_in_transaction(self, manager: DatabaseManager) -> None:
        migrations = self.validate()
        await manager.execute(
            "CREATE TABLE _typerdrive_migrations ("
            "migration_index INTEGER PRIMARY KEY, "
            "migration_id TEXT NOT NULL UNIQUE, "
            "checksum TEXT NOT NULL)"
        )
        await self._apply_migrations_in_transaction(manager, migrations, migrations)

    async def _apply_migrations_in_transaction(
        self,
        manager: DatabaseManager,
        pending: tuple[tuple[Migration, tuple[str, ...]], ...],
        all_migrations: tuple[tuple[Migration, tuple[str, ...]], ...],
    ) -> None:
        for migration, statements in pending:
            applied = await self._verify_history(manager, all_migrations)
            if migration.index in applied:
                continue
            try:
                for statement in statements:
                    await manager.execute(statement)
                await manager.execute(
                    "INSERT INTO _typerdrive_migrations (migration_index, migration_id, checksum) "
                    "VALUES (?, ?, ?)",
                    (migration.index, migration.migration_id, migration.checksum),
                )
            except Exception as error:
                raise DatabaseMigrationError(
                    f"Failed to apply migration {migration.migration_id}: {error}"
                ) from error

    async def get_status(self, database_path: Path | str) -> tuple[list[Migration], list[Migration]]:
        migrations = self.validate()
        path = Path(database_path)
        if not path.exists():
            return [], [migration for migration, _ in migrations]
        try:
            connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
            try:
                table = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = '_typerdrive_migrations'"
                ).fetchone()
                rows = [] if table is None else connection.execute(
                    "SELECT migration_index, migration_id, checksum "
                    "FROM _typerdrive_migrations ORDER BY migration_index"
                ).fetchall()
            finally:
                connection.close()
        except sqlite3.Error as error:
            raise DatabaseMigrationError(f"Failed to inspect database migration status: {error}") from error
        applied = self._validate_rows(rows, migrations)
        applied_migrations = [migration for migration, _ in migrations if migration.index in applied]
        pending_migrations = [migration for migration, _ in migrations if migration.index not in applied]
        return applied_migrations, pending_migrations

    async def _verify_history(
        self, manager: DatabaseManager, migrations: tuple[tuple[Migration, tuple[str, ...]], ...]
    ) -> set[int]:
        rows = await manager.fetch_all(
            "SELECT migration_index, migration_id, checksum "
            "FROM _typerdrive_migrations ORDER BY migration_index"
        )
        return self._validate_rows(rows, migrations)

    @staticmethod
    def _validate_rows(rows, migrations: tuple[tuple[Migration, tuple[str, ...]], ...]) -> set[int]:
        expected = {migration.index: migration for migration, _ in migrations}
        applied: set[int] = set()
        for expected_index, (index, migration_id, checksum) in enumerate(rows, start=1):
            if index != expected_index:
                raise DatabaseMigrationIntegrityError(
                    f"Applied migration index sequence has a gap before {index}"
                )
            migration = expected.get(index)
            if migration is None:
                raise DatabaseMigrationIntegrityError(f"Applied migration index {index} is no longer registered")
            if migration_id != migration.migration_id:
                raise DatabaseMigrationIntegrityError(
                    f"Migration {index} changed identity from {migration_id} to {migration.migration_id}"
                )
            if checksum != migration.checksum:
                raise DatabaseMigrationIntegrityError(f"Migration {migration_id} SQL checksum changed")
            applied.add(index)
        return applied

    @staticmethod
    def _split_sql(sql_text: str) -> tuple[str, ...]:
        statements: list[str] = []
        current = ""
        for character in sql_text:
            current += character
            if character == ";" and sqlite3.complete_statement(current):
                if current.strip():
                    statements.append(current.strip())
                current = ""
        if current.strip() and (not statements or MigrationRegistry._contains_sql_content(current)):
            raise DatabaseMigrationError("Migration SQL contains an incomplete statement")
        return tuple(statements)

    @staticmethod
    def _contains_sql_content(sql_text: str) -> bool:
        index = 0
        while index < len(sql_text):
            if sql_text[index].isspace():
                index += 1
            elif sql_text.startswith("--", index):
                newline = index + 2
                while newline < len(sql_text) and sql_text[newline] not in "\r\n":
                    newline += 1
                if newline == len(sql_text):
                    return False
                index = newline + 1
            elif sql_text.startswith("/*", index):
                end = sql_text.find("*/", index + 2)
                if end == -1:
                    return True
                index = end + 2
            else:
                return True
        return False
