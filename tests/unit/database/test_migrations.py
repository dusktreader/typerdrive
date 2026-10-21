import asyncio
import subprocess
import sys
import time
from pathlib import Path

import pytest
from typerdrive.database.exceptions import DatabaseMigrationError, DatabaseMigrationIntegrityError
from typerdrive.database.migrations import MigrationRegistry
from typerdrive.database.session import DatabaseSession


def run(coro):
    return asyncio.run(coro)


class TestMigrationRegistry:
    def test_registration_assigns_ordered_stable_identifiers(self):
        registry = MigrationRegistry()
        first = registry.register_migration("Create Items", "CREATE TABLE item (id INTEGER);")
        second = registry.register_migration("Add Item Name", "ALTER TABLE item ADD COLUMN name TEXT;")

        assert (first.index, first.migration_id) == (1, "00000001create items")
        assert (second.index, second.migration_id) == (2, "00000002add item name")

    @pytest.mark.parametrize("comment", ["-- trailing comment", "/* trailing comment */"])
    def test_split_sql_accepts_trailing_comments(self, comment: str):
        sql_text = f"CREATE TABLE item (id INTEGER); {comment}"

        assert MigrationRegistry._split_sql(sql_text) == ("CREATE TABLE item (id INTEGER);",)

    @pytest.mark.parametrize(
        "sql_text",
        [
            "CREATE TABLE item (id INTEGER)",
            "CREATE TABLE item (id INTEGER); SELECT",
            "CREATE TABLE item (id INTEGER); /* incomplete comment",
        ],
    )
    def test_split_sql_rejects_incomplete_statements(self, sql_text: str):
        with pytest.raises(DatabaseMigrationError, match="incomplete statement"):
            MigrationRegistry._split_sql(sql_text)

    def test_split_sql_handles_comments_between_statements(self, tmp_path: Path):
        sql_text = (
            "CREATE TABLE item (id INTEGER); -- between statements\n"
            "INSERT INTO item VALUES (1); /* between statements */ INSERT INTO item VALUES (2);"
        )
        registry = MigrationRegistry()
        registry.register_migration("Create Items", sql_text)
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                await registry.apply(manager)
                rows = await manager.fetch_all("SELECT id FROM item ORDER BY id")
                assert [row["id"] for row in rows] == [1, 2]

        run(scenario())

    @pytest.mark.parametrize("description, sql", [("", "CREATE TABLE item (id INTEGER);"), ("create item", "  ")])
    def test_empty_registration_fails_before_database_changes(self, tmp_path: Path, description: str, sql: str):
        registry = MigrationRegistry()
        registry.register_migration(description, sql)
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                with pytest.raises(DatabaseMigrationError):
                    await registry.apply(manager)
                assert (
                    await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = '_typerdrive_migrations'")
                    is None
                )

        run(scenario())

    def test_applies_migrations_in_order_and_tracks_checksums(self, tmp_path: Path):
        registry = MigrationRegistry()
        registry.register_migration("Create Items", "CREATE TABLE item (id INTEGER PRIMARY KEY);")
        registry.register_migration("Add Name", "ALTER TABLE item ADD COLUMN name TEXT;")
        manager = DatabaseSession(tmp_path / "database.sqlite")

        async def scenario():
            async with manager:
                await registry.apply(manager)
                records = await manager.fetch_all(
                    "SELECT migration_index, migration_id, checksum FROM _typerdrive_migrations ORDER BY migration_index"
                )
                columns = await manager.fetch_all("PRAGMA table_info(item)")
                assert [(row[0], row[1]) for row in records] == [
                    (1, "00000001create items"),
                    (2, "00000002add name"),
                ]
                assert all(len(row[2]) == 64 for row in records)
                assert [row[1] for row in columns] == ["id", "name"]

        run(scenario())

    @pytest.mark.parametrize(
        "description, sql_text",
        [
            ("Create Other", "CREATE TABLE item (id INTEGER);"),
            ("Create Items", "CREATE TABLE item (id INTEGER, name TEXT);"),
        ],
    )
    def test_changed_description_or_sql_fails_before_later_migration(
        self, tmp_path: Path, description: str, sql_text: str
    ):
        path = tmp_path / "database.sqlite"
        original = MigrationRegistry()
        original.register_migration("Create Items", "CREATE TABLE item (id INTEGER);")
        run(self.apply_with_manager(original, path))
        changed = MigrationRegistry()
        changed.register_migration(description, sql_text)
        changed.register_migration("Later", "CREATE TABLE later (id INTEGER);")

        async def scenario():
            async with DatabaseSession(path) as manager:
                with pytest.raises(DatabaseMigrationIntegrityError):
                    await changed.apply(manager)
                assert await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'later'") is None

        run(scenario())

    def test_removed_applied_migration_fails_before_later_schema_changes(self, tmp_path: Path):
        path = tmp_path / "database.sqlite"
        original = MigrationRegistry()
        original.register_migration("Create Items", "CREATE TABLE item (id INTEGER);")
        original.register_migration("Add Name", "ALTER TABLE item ADD COLUMN name TEXT;")
        run(self.apply_with_manager(original, path))

        shorter = MigrationRegistry()
        shorter.register_migration("Create Items", "CREATE TABLE item (id INTEGER);")

        async def scenario():
            async with DatabaseSession(path) as manager:
                before = await manager.fetch_all("SELECT name FROM sqlite_master ORDER BY name")
                with pytest.raises(DatabaseMigrationIntegrityError, match="no longer registered"):
                    await shorter.apply(manager)
                after = await manager.fetch_all("SELECT name FROM sqlite_master ORDER BY name")
                assert [row[0] for row in after] == [row[0] for row in before]

        run(scenario())

    def test_missing_applied_index_fails_integrity_validation(self, tmp_path: Path):
        registry = MigrationRegistry()
        registry.register_migration("Create Items", "CREATE TABLE item (id INTEGER);")
        registry.register_migration("Add Name", "ALTER TABLE item ADD COLUMN name TEXT;")
        path = tmp_path / "database.sqlite"

        async def scenario():
            async with DatabaseSession(path) as manager:
                await registry.apply(manager)
                await manager.execute("DELETE FROM _typerdrive_migrations WHERE migration_index = 1")
                with pytest.raises(DatabaseMigrationIntegrityError, match="index sequence"):
                    await registry.apply(manager)

        run(scenario())

    def test_failed_migration_rolls_back_and_can_retry(self, tmp_path: Path):
        path = tmp_path / "database.sqlite"
        registry = MigrationRegistry()
        registry.register_migration("Create Items", "CREATE TABLE item (id INTEGER);")
        registry.register_migration("Broken", "CREATE TABLE partial (id INTEGER); INVALID SQL;")

        async def scenario():
            async with DatabaseSession(path) as manager:
                with pytest.raises(DatabaseMigrationError):
                    await registry.apply(manager)
                assert await manager.fetch_value("SELECT name FROM sqlite_master WHERE name = 'partial'") is None
                assert await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations") == 1

        run(scenario())
        registry = MigrationRegistry()
        registry.register_migration("Create Items", "CREATE TABLE item (id INTEGER);")
        registry.register_migration("Add Name", "ALTER TABLE item ADD COLUMN name TEXT;")
        run(self.apply_with_manager(registry, path))

    def test_simultaneous_migration_runs_apply_once(self, tmp_path: Path):
        path = tmp_path / "database.sqlite"
        registry = MigrationRegistry()
        registry.register_migration("Create Items", "CREATE TABLE item (id INTEGER); INSERT INTO item VALUES (1);")

        async def scenario():
            async def apply():
                async with DatabaseSession(path) as manager:
                    await registry.apply(manager)

            await asyncio.gather(apply(), apply())
            async with DatabaseSession(path) as manager:
                assert await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations") == 1
                assert await manager.fetch_value("SELECT COUNT(*) FROM item") == 1

        run(scenario())

    def test_simultaneous_process_migrations_apply_once(self, tmp_path: Path):
        path = tmp_path / "database.sqlite"
        start = tmp_path / "start"
        ready_files = [tmp_path / f"ready-{index}" for index in range(2)]
        script = """
import asyncio
import sys
import time
from pathlib import Path
from typerdrive.database.session import DatabaseSession
from typerdrive.database.migrations import MigrationRegistry

path, start, ready = sys.argv[1:]
Path(ready).touch()
while not Path(start).exists():
    time.sleep(0.01)
registry = MigrationRegistry()
registry.register_migration("Create Items", "CREATE TABLE item (id INTEGER); INSERT INTO item VALUES (1);")
async def apply():
    async with DatabaseSession(path) as manager:
        await registry.apply(manager)
asyncio.run(apply())
"""
        processes = [
            subprocess.Popen(
                [sys.executable, "-c", script, str(path), str(start), str(ready)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for ready in ready_files
        ]
        try:
            deadline = time.monotonic() + 20
            while not all(ready.exists() for ready in ready_files):
                assert all(process.poll() is None for process in processes)
                assert time.monotonic() < deadline
                time.sleep(0.01)
            start.touch()
            outputs = [process.communicate(timeout=40) for process in processes]
            assert [process.returncode for process in processes] == [0, 0], outputs
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

        async def verify():
            async with DatabaseSession(path) as manager:
                assert await manager.fetch_value("SELECT COUNT(*) FROM _typerdrive_migrations") == 1
                assert await manager.fetch_value("SELECT COUNT(*) FROM item") == 1

        run(verify())

    @staticmethod
    async def apply_with_manager(registry: MigrationRegistry, path: Path):
        async with DatabaseSession(path) as manager:
            await registry.apply(manager)
