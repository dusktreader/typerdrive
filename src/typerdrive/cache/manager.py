"""
Provide a class for managing the `typerdrive` cache feature using diskcache.
"""

import re
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

import humanize
from loguru import logger
from rich import box
from rich.table import Table

from typerdrive.cache.typed_cache import TypedCache

from typerdrive.cache.exceptions import (
    CacheClearError,
    CacheError,
    CacheInitError,
    CacheLoadError,
    CacheStoreError,
)
from typerdrive.cache.models import CacheStats
from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.constants import EvictionPolicy
from typerdrive.format import terminal_message


class CacheManager:
    """
    Manage the `typerdrive` cache feature using diskcache library.

    This provides a traditional key-value cache with TTL support, eviction policies,
    and efficient disk-based storage.
    """

    cache_dir: Path
    """ The directory where the cache database is stored. """

    cache: TypedCache
    """ The underlying TypedCache instance (wrapper around diskcache.Cache). """

    def __init__(
        self,
        size_limit: int = 2**30,
        eviction_policy: EvictionPolicy = EvictionPolicy.LEAST_RECENTLY_USED,
    ):
        """
        Initialize the cache manager.

        Parameters:
            size_limit: Maximum size of the cache in bytes (default: 1GB)
            eviction_policy: Eviction policy to use when size limit is reached
        """
        config: TyperdriveConfig = get_typerdrive_config()
        self.cache_dir = config.cache_dir

        with CacheInitError.handle_errors("Failed to initialize cache"):
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache = TypedCache(
                directory=str(self.cache_dir),
                size_limit=size_limit,
                eviction_policy=eviction_policy.value,
            )

    def set(
        self,
        key: str,
        value: Any,
        expire: timedelta | None = None,
        group: str | None = None,
    ) -> bool:
        """
        Set a value in the cache.

        Parameters:
            key: The cache key
            value: The value to store (must be picklable)
            expire: Time until the key expires (None for no expiration)
            group: Optional group for organizing related cache entries

        Returns:
            True if the value was successfully set
        """
        logger.debug(f"Setting cache key: {key}")

        with CacheStoreError.handle_errors(f"Failed to store value for key '{key}'"):
            # Convert timedelta to seconds for diskcache
            expire_seconds = expire.total_seconds() if expire else None
            return self.cache.set(key, value, expire=expire_seconds, tag=group)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.

        Parameters:
            key: The cache key
            default: Value to return if key is not found

        Returns:
            The cached value or default if not found
        """
        logger.debug(f"Getting cache key: {key}")

        with CacheLoadError.handle_errors(f"Failed to load value for key '{key}'"):
            return self.cache.get(key, default=default)

    def setdefault(
        self,
        key: str,
        default: Any = None,
        expire: timedelta | None = None,
        group: str | None = None,
    ) -> Any:
        """
        Get a value from the cache, setting it to default if not found.

        This mimics dict.setdefault() behavior: if the key exists in the cache,
        return its value. Otherwise, set the key to the default value and return it.

        Parameters:
            key: The cache key
            default: Value to set and return if key is not found
            expire: Time until the key expires (None for no expiration)
            group: Optional group for organizing related cache entries

        Returns:
            The cached value if it exists, otherwise the default value (which is also stored)
        """
        logger.debug(f"Getting or setting default for cache key: {key}")

        with CacheLoadError.handle_errors(f"Failed to get or set default for key '{key}'"):
            # Use a sentinel value to detect cache misses
            sentinel = object()
            value = self.cache.get(key, default=sentinel)

            if value is not sentinel:
                return value

            # Key doesn't exist, set the default value
            expire_seconds = expire.total_seconds() if expire else None
            self.cache.set(key, default, expire=expire_seconds, tag=group)
            return default

    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        Parameters:
            key: The cache key to delete

        Returns:
            True if the key was found and deleted
        """
        logger.debug(f"Deleting cache key: {key}")

        with CacheClearError.handle_errors(f"Failed to delete key '{key}'"):
            return self.cache.delete(key)

    def clear(self, group: str | None = None) -> int:
        """
        Remove items from the cache.

        Parameters:
            group: If provided, only remove entries with this group. Otherwise, remove all items.

        Returns:
            The number of items removed
        """
        if group:
            logger.debug(f"Evicting cache entries with group: {group}")
            with CacheClearError.handle_errors(f"Failed to evict group '{group}'"):
                return self.cache.evict(group)
        else:
            logger.debug("Clearing entire cache")
            with CacheClearError.handle_errors("Failed to clear cache"):
                count = len(self.cache)
                self.cache.clear()
                return count

    def keys(self, pattern: str | None = None, group: str | None = None) -> list[str]:
        """
        Get keys in the cache, optionally filtered by pattern and/or group.

        Parameters:
            pattern: Optional regex pattern to filter keys
            group: Optional group to filter by

        Returns:
            List of matching cache keys
        """
        with CacheError.handle_errors("Failed to retrieve cache keys"):
            # Convert keys to strings (diskcache may return bytes)
            all_keys: list[str] = [k.decode("utf-8") if isinstance(k, bytes) else k for k in self.cache.iterkeys()]

            # Filter by pattern if provided
            if pattern:
                regex = re.compile(pattern)
                all_keys = [k for k in all_keys if regex.search(k)]

            # Filter by group if provided
            # Note: diskcache doesn't provide a way to query keys by group directly,
            # so we need to check each key's group
            if group:
                filtered_keys: list[str] = []
                for key in all_keys:
                    try:
                        # TypedCache.get() with tag=True returns tuple[value, tag_str]
                        _, key_group = self.cache.get(key, tag=True)
                        if key_group == group:
                            filtered_keys.append(key)
                    except Exception:
                        pass
                all_keys = filtered_keys

            return all_keys

    def get_group(self, key: str) -> str | None:
        """
        Get the group associated with a key.

        Parameters:
            key: The cache key

        Returns:
            The group associated with the key, or None if no group or key doesn't exist
        """
        with CacheError.handle_errors(f"Failed to get group for key '{key}'"):
            # Use TypedCache's tag parameter to retrieve the group
            # When tag=True, get() returns (value, tag) tuple
            try:
                _, group = self.cache.get(key, tag=True)
                return group
            except KeyError:
                return None

    def get_ttl(self, key: str) -> str:
        """
        Get the time-to-live for a cache key in human-readable format.

        Parameters:
            key: The cache key

        Returns:
            Human-readable TTL string (e.g., "2 hours", "never"), or "expired" if the key doesn't exist
        """
        with CacheError.handle_errors(f"Failed to get TTL for key '{key}'"):
            # Get expire_time from TypedCache
            # TypedCache.get() with expire_time=True returns tuple[value, expire_time_float]
            value, expire_time = self.cache.get(key, default=None, expire_time=True)

            # If value is None, the key doesn't exist
            if value is None:
                return "expired"

            # expire_time is None if no expiration set
            if expire_time is None:
                return "never"

            # Calculate remaining time
            current_time = time.time()
            remaining_seconds = expire_time - current_time

            if remaining_seconds <= 0:
                return "expired"

            # Use humanize for human-readable format
            return humanize.naturaldelta(timedelta(seconds=remaining_seconds))

    def stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats object with cache statistics
        """
        with CacheError.handle_errors("Failed to retrieve cache stats"):
            # TypedCache.stats() returns tuple[int, int] for (hits, misses)
            hits, misses = self.cache.stats(enable=True)
            return CacheStats(
                hits=hits,
                misses=misses,
                size=len(self.cache),
                volume=self.cache.volume(),
            )

    def show(
        self,
        pattern: str | None = None,
        group: str | None = None,
        show_stats: bool = False,
        include_stats: bool = True,
    ) -> None:
        """
        Display cache contents or statistics.

        Parameters:
            pattern: Optional regex pattern to filter keys
            group: Optional group to filter entries
            show_stats: If True, show statistics instead of entries
            include_stats: If True and show_stats is False, include stats summary at bottom of entries
        """
        from rich.console import Group as RichGroup

        if show_stats:
            stats_data = self.stats()
            table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
            table.add_column("Metric")
            table.add_column("Value")

            table.add_row("Size (entries)", str(stats_data.size))
            table.add_row("Volume (bytes)", str(stats_data.volume))
            table.add_row("Hits", str(stats_data.hits))
            table.add_row("Misses", str(stats_data.misses))

            terminal_message(table, subject="Cache Statistics")
        else:
            keys = self.keys(pattern=pattern, group=group)
            if not keys:
                terminal_message("No cache entries found")
                return

            # Build filter string for title
            filters: list[str] = []
            if pattern:
                filters.append(f"pattern={pattern}")
            if group:
                filters.append(f"group={group}")
            filter_str = f" ({', '.join(filters)})" if filters else ""

            # Build entries table
            entries_table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
            entries_table.add_column("Key", style="green")
            entries_table.add_column("Group", style="yellow")
            entries_table.add_column("TTL", style="blue")

            for key in sorted(keys):
                key_group = self.get_group(key) or ""
                key_ttl = self.get_ttl(key)
                entries_table.add_row(key, key_group, key_ttl)

            if include_stats:
                # Get stats
                stats_data = self.stats()

                # Build stats table
                stats_table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
                stats_table.add_column("Entries", justify="right")
                stats_table.add_column("Volume", justify="right")
                stats_table.add_column("Hits", justify="right")
                stats_table.add_column("Misses", justify="right")
                stats_table.add_row(
                    str(stats_data.size),
                    f"{stats_data.volume:,} bytes",
                    str(stats_data.hits),
                    str(stats_data.misses),
                )

                # Combine tables
                combined = RichGroup(entries_table, "", stats_table)
                terminal_message(combined, subject=f"Cache contains {len(keys)} entries{filter_str}")
            else:
                # Just show entries table
                terminal_message(entries_table, subject=f"Cache contains {len(keys)} entries{filter_str}")
