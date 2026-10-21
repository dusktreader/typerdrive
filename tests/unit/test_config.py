import os
from pathlib import Path
from unittest.mock import patch

from typerdrive.config import TyperdriveConfig, get_typerdrive_config, set_typerdrive_config


class TestTyperdriveConfig:
    def test_default_config(self):
        config = TyperdriveConfig(app_name="test_app")

        # Should have default values
        assert config.app_name == "test_app"
        assert config.version is None
        assert config.description is None
        assert config.log_file_rotation == "1 week"
        assert config.log_file_retention == "1 month"
        assert config.log_file_compression == "tar.gz"
        assert config.log_file_name == "app.log"
        assert config.console_width is None
        assert config.console_ascii_only is False

    def test_log_dir_uses_xdg_state_home(self):
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state"}):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path("/custom/state/test_app/logs")
            assert config.log_dir == expected

    def test_log_dir_default_fallback(self):
        # Remove XDG_STATE_HOME if it exists
        env = {k: v for k, v in os.environ.items() if k != "XDG_STATE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path.home() / ".local/state/test_app/logs"
            assert config.log_dir == expected

    def test_settings_path_uses_xdg_state_home(self):
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state"}):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path("/custom/state/test_app/settings.json")
            assert config.settings_path == expected

    def test_settings_path_default_fallback(self):
        env = {k: v for k, v in os.environ.items() if k != "XDG_STATE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path.home() / ".local/state/test_app/settings.json"
            assert config.settings_path == expected

    def test_cache_dir_uses_xdg_cache_home(self):
        with patch.dict(os.environ, {"XDG_CACHE_HOME": "/custom/cache"}):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path("/custom/cache/test_app")
            assert config.cache_dir == expected

    def test_cache_dir_default_fallback(self):
        env = {k: v for k, v in os.environ.items() if k != "XDG_CACHE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path.home() / ".cache/test_app"
            assert config.cache_dir == expected

    def test_database_path_uses_xdg_state_home(self):
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state"}):
            config = TyperdriveConfig(app_name="test_app")
            assert config.database_path == Path("/custom/state/test_app/db.sqlite")

    def test_database_path_default_fallback(self):
        env = {k: v for k, v in os.environ.items() if k != "XDG_STATE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            config = TyperdriveConfig(app_name="test_app")
            assert config.database_path == Path.home() / ".local/state/test_app/db.sqlite"

    def test_database_path_isolated_by_app_name_and_state_home(self):
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state", "XDG_CACHE_HOME": "/custom/cache"}):
            first = TyperdriveConfig(app_name="first")
            second = TyperdriveConfig(app_name="second")
            assert first.database_path != second.database_path
            assert first.database_path.parent == Path("/custom/state/first")
            assert first.database_path != first.cache_dir
            assert first.database_path != first.files_dir

    def test_custom_home_overrides(self):
        config = TyperdriveConfig(
            app_name="test_app",
            state_home=Path("/custom/state"),
            cache_home=Path("/custom/cache"),
        )

        assert config.state_home == Path("/custom/state")
        assert config.cache_home == Path("/custom/cache")
        assert config.log_dir == Path("/custom/state/test_app/logs")
        assert config.settings_path == Path("/custom/state/test_app/settings.json")
        assert config.files_dir == Path("/custom/state/test_app/files")
        assert config.database_path == Path("/custom/state/test_app/db.sqlite")
        assert config.cache_dir == Path("/custom/cache/test_app")

    def test_custom_app_name(self):
        config = TyperdriveConfig(app_name="my_custom_app")

        assert "my_custom_app" in str(config.log_dir)
        assert "my_custom_app" in str(config.settings_path)
        assert "my_custom_app" in str(config.cache_dir)


class TestConfigGettersAndSetters:
    def test_get_config_returns_copy(self):
        config1 = get_typerdrive_config()
        config2 = get_typerdrive_config()

        # Should be equal but not the same object
        assert config1.model_dump() == config2.model_dump()
        assert config1 is not config2

    def test_set_config_updates_global_config(self):
        original = get_typerdrive_config()

        try:
            set_typerdrive_config(
                app_name="new_test_app",
                version="1.2.3",
                description="A test app",
                console_width=120,
                state_home=Path("/custom/state"),
                cache_home=Path("/custom/cache"),
            )
            updated = get_typerdrive_config()

            assert updated.app_name == "new_test_app"
            assert updated.version == "1.2.3"
            assert updated.description == "A test app"
            assert updated.console_width == 120
            assert updated.state_home == Path("/custom/state")
            assert updated.cache_home == Path("/custom/cache")
        finally:
            # Restore original config
            set_typerdrive_config(**original.model_dump())

    def test_set_config_preserves_other_values(self):
        original = get_typerdrive_config()

        try:
            set_typerdrive_config(console_width=100)
            updated = get_typerdrive_config()

            # Changed value
            assert updated.console_width == 100

            # Preserved values
            assert updated.app_name == original.app_name
            assert updated.state_home == original.state_home
            assert updated.cache_home == original.cache_home
            assert updated.log_file_rotation == original.log_file_rotation
            assert updated.log_file_retention == original.log_file_retention
        finally:
            # Restore original config
            set_typerdrive_config(**original.model_dump())
