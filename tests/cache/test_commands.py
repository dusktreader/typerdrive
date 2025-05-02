from pathlib import Path

import typer

from typerdrive.cache.commands import add_clear, add_show, add_cache_subcommand
from typerdrive.cache.manager import CacheManager
from typerdrive.constants import ExitCode

from tests.helpers import match_help, match_output


class TestClear:
    def test_clear__removes_a_single_entry_with_path_param(self, fake_cache_path: Path):
        cli = typer.Typer()
        add_clear(cli)
        full_path = fake_cache_path / "jawa/ewok.txt"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("hive of scum and villainy")

        match_output(
            cli,
            "--path=jawa/ewok.txt",
            expected_pattern="Cleared entry at cache target jawa/ewok.txt",
            prog_name="test",
        )

        assert not full_path.exists()

    def test_clear__raises_exception_if_no_item_is_found_at_path(self):
        cli = typer.Typer()

        add_clear(cli)

        match_output(
            cli,
            "--path=jawa/ewok.txt",
            exit_code=ExitCode.GENERAL_ERROR,
            expected_pattern="Failed to clear cache target jawa/ewok.txt",
            prog_name="test",
        )

    def test_clear__help_text(self):
        cli = typer.Typer()

        add_clear(cli)

        expected_pattern = [
            "Options",
            r"--path TEXT Clear only the entry .* \[default: None\]",
        ]
        match_help(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    def test_clear_all__removes_all_cached_files_with_no_path_arg(self, fake_cache_path: Path):
        cli = typer.Typer()
        add_clear(cli)

        manager: CacheManager = CacheManager("test")
        manager.store_text("hive of scum and villainy", "jawa/ewok")
        manager.store_bytes(b"that's no moon", "hutt")

        match_output(
            cli,
            expected_pattern="Cleared all 2 files from cache",
            input="y",
            prog_name="test",
        )

        assert not (fake_cache_path / "jawa/ewok").exists()
        assert not (fake_cache_path / "hutt").exists()

        assert len([p for p in fake_cache_path.iterdir()]) == 0

    def test_clear_all__does_nothing_if_confirmation_not_provided(self, fake_cache_path: Path):
        cli = typer.Typer()
        add_clear(cli)

        manager: CacheManager = CacheManager("test")
        manager.store_text("hive of scum and villainy", "jawa/ewok")
        manager.store_bytes(b"that's no moon", "hutt")

        match_output(
            cli,
            exit_code=1,
            input="n",
            prog_name="test",
        )

        assert (fake_cache_path / "jawa/ewok").exists()
        assert (fake_cache_path / "hutt").exists()

        assert len([p for p in fake_cache_path.iterdir()]) == 2


class TestShow:
    def test_show__shows_cache_directory_tree(self, fake_cache_path: Path):
        manager: CacheManager = CacheManager("test")
        manager.store_text("hive of scum and villainy", "jawa/ewok.txt")
        manager.store_bytes(b"that's no moon", "hutt")

        cli = typer.Typer()

        add_show(cli)

        expected_pattern = f"""
            📂 {fake_cache_path}
            ├── 📂 jawa
            │   └── 📄 ewok.txt (25 Bytes)
            └── 📄 hutt (14 Bytes)
        """
        match_output(
            cli,
            expected_pattern=expected_pattern,
            escape_parens=True,
            prog_name="test",
        )


class TestSubcommand:
    def test_add_cache_subcommand(self):
        cli = typer.Typer()

        add_cache_subcommand(cli)

        expected_pattern = [
            r"cache.*Manage cache for the app",
        ]
        match_help(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        expected_pattern = [
            "clear",
            "show",
        ]
        match_output(
            cli,
            "cache",
            "--help",
            exit_code=0,
            expected_pattern=expected_pattern,
            prog_name="test",
        )
