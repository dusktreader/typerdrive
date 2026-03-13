import pytest
import typer
from typerdrive.cache.commands import add_cache_subcommand, add_clear, add_show
from typerdrive.cache.manager import CacheManager

from tests.unit.helpers import match_help, match_output


class TestClear:
    def test_clear__help_text(self):
        cli = typer.Typer()

        add_clear(cli)

        expected_pattern = [
            "Options",
            r"--group TEXT.*Clear only entries with this group",
        ]
        match_help(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    @pytest.mark.usefixtures("fake_cache_path")
    def test_clear_all__removes_all_cached_entries(self):
        cli = typer.Typer()
        add_clear(cli)

        manager: CacheManager = CacheManager()
        manager.set("jawa/ewok", "hive of scum and villainy")
        manager.set("hutt", b"that's no moon")

        match_output(
            cli,
            expected_pattern="Cleared 2 entries from cache",
            input="y",
            prog_name="test",
        )

        assert manager.get("jawa/ewok") is None
        assert manager.get("hutt") is None
        assert len(manager.keys()) == 0

    @pytest.mark.usefixtures("fake_cache_path")
    def test_clear_all__does_nothing_if_confirmation_not_provided(self):
        cli = typer.Typer()
        add_clear(cli)

        manager: CacheManager = CacheManager()
        manager.set("jawa/ewok", "hive of scum and villainy")
        manager.set("hutt", b"that's no moon")

        match_output(
            cli,
            exit_code=1,
            input="n",
            prog_name="test",
        )

        assert manager.get("jawa/ewok") == "hive of scum and villainy"
        assert manager.get("hutt") == b"that's no moon"
        assert len(manager.keys()) == 2

    @pytest.mark.usefixtures("fake_cache_path")
    def test_clear__evicts_by_group(self):
        cli = typer.Typer()
        add_clear(cli)

        manager: CacheManager = CacheManager()
        manager.set("jawa/ewok", "hive of scum and villainy", group="star_wars")
        manager.set("hutt", b"that's no moon", group="star_wars")
        manager.set("borg", b"resistance is futile", group="star_trek")

        match_output(
            cli,
            "--group=star_wars",
            expected_pattern="Cleared 2 entries with group 'star_wars'",
            input="y",
            prog_name="test",
        )

        assert manager.get("jawa/ewok") is None
        assert manager.get("hutt") is None
        assert manager.get("borg") == b"resistance is futile"


class TestShow:
    @pytest.mark.usefixtures("fake_cache_path")
    def test_show__shows_cache_table(self):
        manager: CacheManager = CacheManager()
        manager.set("jawa/ewok", "hive of scum and villainy")
        manager.set("hutt", b"that's no moon")

        cli = typer.Typer()

        add_show(cli)

        expected_pattern = [
            "Cache contains 2 entries",
            "Key",
            "Group",
            "TTL",
            "hutt",
            "jawa/ewok",
        ]
        match_output(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    @pytest.mark.usefixtures("fake_cache_path")
    def test_show__displays_stats(self):
        manager: CacheManager = CacheManager()
        manager.set("key1", "value1")
        manager.set("key2", "value2")

        # Generate some hits/misses
        manager.get("key1")
        manager.get("nonexistent")

        cli = typer.Typer()

        add_show(cli)

        expected_pattern = [
            "Cache Statistics",
            "Size",
            "Volume",
            "Hits",
            "Misses",
        ]
        match_output(
            cli,
            "--stats",
            expected_pattern=expected_pattern,
            prog_name="test",
        )


class TestSubcommand:
    @pytest.mark.usefixtures("fake_cache_path")
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
