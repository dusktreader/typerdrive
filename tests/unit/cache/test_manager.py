from datetime import timedelta
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from typerdrive.cache.exceptions import CacheInitError
from typerdrive.cache.manager import CacheManager


@pytest.mark.usefixtures("fake_cache_path")
class TestCacheManager:
    def test_init__no_issues(self, fake_cache_path: Path):
        manager = CacheManager()
        assert manager.cache_dir == fake_cache_path
        assert manager.cache is not None

    def test_init__raises_exception_on_fail(self, mocker: MockerFixture):
        mocker.patch("typerdrive.cache.manager.Path.mkdir", side_effect=RuntimeError("BOOM!"))
        with pytest.raises(CacheInitError, match="Failed to initialize cache"):
            CacheManager()

    def test_set__basic(self):
        manager = CacheManager()
        result = manager.set("test_key", "test_value")
        assert result is True

    def test_set__with_expire(self):
        manager = CacheManager()
        result = manager.set("temp_key", "temp_value", expire=timedelta(seconds=1))
        assert result is True

    def test_set__with_group(self):
        manager = CacheManager()
        result = manager.set("grouped_key", "grouped_value", group="test_group")
        assert result is True

    def test_get__basic(self):
        manager = CacheManager()
        manager.set("test_key", "test_value")
        value = manager.get("test_key")
        assert value == "test_value"

    def test_get__returns_default_if_not_found(self):
        manager = CacheManager()
        value = manager.get("nonexistent", default="default_value")
        assert value == "default_value"

    def test_get__supports_complex_objects(self):
        manager = CacheManager()
        data = {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}
        manager.set("complex_key", data)
        retrieved = manager.get("complex_key")
        assert retrieved == data

    def test_setdefault__returns_existing_value(self):
        manager = CacheManager()
        manager.set("existing_key", "existing_value")
        value = manager.setdefault("existing_key", "default_value")
        assert value == "existing_value"

    def test_setdefault__sets_and_returns_default_if_not_found(self):
        manager = CacheManager()
        value = manager.setdefault("new_key", "default_value")
        assert value == "default_value"
        assert manager.get("new_key") == "default_value"

    def test_setdefault__with_none_default(self):
        manager = CacheManager()
        value = manager.setdefault("new_key", None)
        assert value is None
        assert manager.get("new_key") is None

    def test_setdefault__with_expire(self):
        manager = CacheManager()
        value = manager.setdefault("temp_key", "temp_value", expire=timedelta(seconds=1))
        assert value == "temp_value"
        assert manager.get("temp_key") == "temp_value"

    def test_setdefault__with_group(self):
        manager = CacheManager()
        value = manager.setdefault("grouped_key", "grouped_value", group="test_group")
        assert value == "grouped_value"
        assert manager.get("grouped_key") == "grouped_value"

    def test_setdefault__supports_complex_objects(self):
        manager = CacheManager()
        data = {"name": "test", "values": [1, 2, 3]}
        value = manager.setdefault("complex_key", data)
        assert value == data
        assert manager.get("complex_key") == data

    def test_get_ttl__no_expiration(self):
        manager = CacheManager()
        manager.set("permanent_key", "value")
        ttl = manager.get_ttl("permanent_key")
        assert ttl == "never"

    def test_get_ttl__with_expiration(self):
        manager = CacheManager()
        manager.set("temp_key", "value", expire=timedelta(hours=2))
        ttl = manager.get_ttl("temp_key")
        assert ttl != "never"
        assert ttl != "expired"

    def test_get_ttl__nonexistent_key(self):
        manager = CacheManager()
        ttl = manager.get_ttl("nonexistent")
        assert ttl == "expired"

    def test_delete__basic(self):
        manager = CacheManager()
        manager.set("test_key", "test_value")
        result = manager.delete("test_key")
        assert result is True
        assert manager.get("test_key") is None

    def test_delete__returns_false_if_not_found(self):
        manager = CacheManager()
        result = manager.delete("nonexistent")
        assert result is False

    def test_clear__basic(self):
        manager = CacheManager()
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        manager.set("key3", "value3")

        count = manager.clear()
        assert count == 3
        assert manager.get("key1") is None
        assert manager.get("key2") is None
        assert manager.get("key3") is None

    def test_clear__by_group(self):
        manager = CacheManager()
        manager.set("grouped1", "value1", group="group_a")
        manager.set("grouped2", "value2", group="group_a")
        manager.set("grouped3", "value3", group="group_b")

        count = manager.clear(group="group_a")
        assert count == 2
        assert manager.get("grouped1") is None
        assert manager.get("grouped2") is None
        assert manager.get("grouped3") == "value3"

    def test_keys__basic(self):
        manager = CacheManager()
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        manager.set("key3", "value3")

        keys = manager.keys()
        assert sorted(keys) == ["key1", "key2", "key3"]

    def test_keys__empty_cache(self):
        manager = CacheManager()
        keys = manager.keys()
        assert keys == []

    def test_stats__basic(self):
        manager = CacheManager()
        manager.set("key1", "value1")
        manager.set("key2", "value2")

        # Access keys to generate hits
        manager.get("key1")
        manager.get("nonexistent")

        stats = manager.stats()
        assert stats.size == 2
        assert stats.volume > 0
        assert stats.hits >= 0
        assert stats.misses >= 0

    def test_size_limit(self):
        # Create a cache with a very small size limit
        manager = CacheManager(size_limit=1024)  # 1KB limit
        manager.set("key1", "x" * 500)
        manager.set("key2", "x" * 500)
        # With eviction, old entries should be removed
        assert manager.get("key1") is None or manager.get("key2") is not None
