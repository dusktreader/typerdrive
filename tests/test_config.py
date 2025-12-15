"""Tests for typerdrive.config module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from typerdrive.config import TyperdriveConfig, get_typerdrive_config, set_typerdrive_config


class TestTyperdriveConfig:
    """Tests for TyperdriveConfig class."""

    def test_default_config(self):
        """Test that default config uses sensible defaults."""
        config = TyperdriveConfig(app_name="test_app")

        # Should have default values
        assert config.app_name == "test_app"
        assert config.log_file_rotation == "1 week"
        assert config.log_file_retention == "1 month"
        assert config.log_file_compression == "tar.gz"
        assert config.log_file_name == "app.log"
        assert config.console_width is None
        assert config.console_ascii_only is False

    def test_log_dir_uses_xdg_state_home(self):
        """Test that log_dir uses XDG_STATE_HOME."""
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state"}):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path("/custom/state/test_app/logs")
            assert config.log_dir == expected

    def test_log_dir_default_fallback(self):
        """Test that log_dir falls back to ~/.local/state when XDG_STATE_HOME is not set."""
        # Remove XDG_STATE_HOME if it exists
        env = {k: v for k, v in os.environ.items() if k != "XDG_STATE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path.home() / ".local/state/test_app/logs"
            assert config.log_dir == expected

    def test_settings_path_uses_xdg_state_home(self):
        """Test that settings_path uses XDG_STATE_HOME."""
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state"}):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path("/custom/state/test_app/settings.json")
            assert config.settings_path == expected

    def test_settings_path_default_fallback(self):
        """Test that settings_path falls back to ~/.local/state when XDG_STATE_HOME is not set."""
        env = {k: v for k, v in os.environ.items() if k != "XDG_STATE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path.home() / ".local/state/test_app/settings.json"
            assert config.settings_path == expected

    def test_cache_dir_uses_xdg_cache_home(self):
        """Test that cache_dir uses XDG_CACHE_HOME."""
        with patch.dict(os.environ, {"XDG_CACHE_HOME": "/custom/cache"}):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path("/custom/cache/test_app")
            assert config.cache_dir == expected

    def test_cache_dir_default_fallback(self):
        """Test that cache_dir falls back to ~/.cache when XDG_CACHE_HOME is not set."""
        env = {k: v for k, v in os.environ.items() if k != "XDG_CACHE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            config = TyperdriveConfig(app_name="test_app")
            expected = Path.home() / ".cache/test_app"
            assert config.cache_dir == expected

    def test_custom_app_name(self):
        """Test that custom app names are reflected in paths."""
        config = TyperdriveConfig(app_name="my_custom_app")

        assert "my_custom_app" in str(config.log_dir)
        assert "my_custom_app" in str(config.settings_path)
        assert "my_custom_app" in str(config.cache_dir)


class TestConfigGettersAndSetters:
    """Tests for get_typerdrive_config and set_typerdrive_config functions."""

    def test_get_config_returns_copy(self):
        """Test that get_typerdrive_config returns a copy of the config."""
        config1 = get_typerdrive_config()
        config2 = get_typerdrive_config()

        # Should be equal but not the same object
        assert config1.model_dump() == config2.model_dump()
        assert config1 is not config2

    def test_set_config_updates_global_config(self):
        """Test that set_typerdrive_config updates the global config."""
        original = get_typerdrive_config()

        try:
            set_typerdrive_config(app_name="new_test_app", console_width=120)
            updated = get_typerdrive_config()

            assert updated.app_name == "new_test_app"
            assert updated.console_width == 120
        finally:
            # Restore original config
            set_typerdrive_config(**original.model_dump())

    def test_set_config_preserves_other_values(self):
        """Test that set_typerdrive_config preserves values not being updated."""
        original = get_typerdrive_config()

        try:
            set_typerdrive_config(console_width=100)
            updated = get_typerdrive_config()

            # Changed value
            assert updated.console_width == 100

            # Preserved values
            assert updated.app_name == original.app_name
            assert updated.log_file_rotation == original.log_file_rotation
            assert updated.log_file_retention == original.log_file_retention
        finally:
            # Restore original config
            set_typerdrive_config(**original.model_dump())
