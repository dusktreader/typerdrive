"""
Typed wrapper around diskcache.Cache for type safety.

This module provides a thin wrapper around diskcache.Cache that adds proper type
annotations. The wrapper uses typing.cast() with inline type ignores to handle
the lack of type stubs in the diskcache library.
"""

from collections.abc import Iterator
from typing import Any, Literal, cast, overload

from diskcache import Cache


class TypedCache:
    """
    Type-safe wrapper around diskcache.Cache.

    This class provides the same interface as diskcache.Cache but with proper
    type annotations. It uses typing.cast() internally to handle the fact that
    diskcache has no type stubs.
    """

    _cache: Cache
    """The underlying diskcache.Cache instance."""

    def __init__(
        self,
        directory: str | None = None,
        timeout: int = 60,
        **settings: Any,
    ):
        """
        Initialize the typed cache.

        Parameters:
            directory: Directory path for cache storage
            timeout: Timeout in seconds for cache operations
            **settings: Additional settings passed to diskcache.Cache
        """
        self._cache = Cache(directory=directory, timeout=timeout, **settings)  # type: ignore[call-arg]

    def set(
        self,
        key: str,
        value: Any,
        expire: float | None = None,
        read: bool = False,
        tag: str | None = None,
        retry: bool = False,
    ) -> bool:
        """
        Set key to value in cache.

        Parameters:
            key: Cache key
            value: Value to store
            expire: Seconds until expiration (None = never)
            read: Not used
            tag: Group/tag for organizing entries
            retry: Whether to retry on failure

        Returns:
            True if value was successfully stored
        """
        result: bool = self._cache.set(key, value, expire=expire, read=read, tag=tag, retry=retry)  # type: ignore[assignment]
        return result

    @overload
    def get(
        self,
        key: str,
        default: Any = None,
        *,
        read: bool = False,
        expire_time: Literal[True],
        tag: Literal[False] = False,
        retry: bool = False,
    ) -> tuple[Any, float | None]: ...

    @overload
    def get(
        self,
        key: str,
        default: Any = None,
        *,
        read: bool = False,
        expire_time: Literal[False] = False,
        tag: Literal[True],
        retry: bool = False,
    ) -> tuple[Any, str | None]: ...

    @overload
    def get(
        self,
        key: str,
        default: Any = None,
        *,
        read: bool = False,
        expire_time: Literal[False] = False,
        tag: Literal[False] = False,
        retry: bool = False,
    ) -> Any: ...

    def get(
        self,
        key: str,
        default: Any = None,
        read: bool = False,
        expire_time: bool = False,
        tag: bool = False,
        retry: bool = False,
    ) -> Any | tuple[Any, str | None] | tuple[Any, float | None]:
        """
        Get value for key from cache.

        Parameters:
            key: Cache key
            default: Value to return if key not found
            read: Not used
            expire_time: If True, return (value, expire_time) tuple
            tag: If True, return (value, tag) tuple
            retry: Whether to retry on failure

        Returns:
            - If expire_time=True: tuple[value, expire_time]
            - If tag=True: tuple[value, tag_string]
            - Otherwise: value
        """
        if expire_time:
            result_with_expire: tuple[Any, float | None] = cast(  # type: ignore[assignment]
                tuple[Any, float | None],
                self._cache.get(key, default=default, read=read, expire_time=True, tag=False, retry=retry),
            )
            return result_with_expire
        elif tag:
            result_with_tag: tuple[Any, str | None] = cast(  # type: ignore[assignment]
                tuple[Any, str | None],
                self._cache.get(key, default=default, read=read, expire_time=False, tag=True, retry=retry),
            )
            return result_with_tag
        else:
            value: Any = self._cache.get(key, default=default, read=read, expire_time=False, tag=False, retry=retry)  # type: ignore[assignment]
            return value

    def delete(self, key: str, retry: bool = False) -> bool:
        """
        Delete key from cache.

        Parameters:
            key: Cache key to delete
            retry: Whether to retry on failure

        Returns:
            True if key was found and deleted
        """
        result: bool = self._cache.delete(key, retry=retry)  # type: ignore[assignment]
        return result

    def clear(self, retry: bool = False) -> int:
        """
        Remove all items from cache.

        Parameters:
            retry: Whether to retry on failure

        Returns:
            Number of items removed
        """
        result: int = self._cache.clear(retry=retry)  # type: ignore[assignment]
        return result

    def evict(self, tag: str, retry: bool = False) -> int:
        """
        Remove all items with the given tag.

        Parameters:
            tag: Tag to evict
            retry: Whether to retry on failure

        Returns:
            Number of items removed
        """
        result: int = self._cache.evict(tag, retry=retry)  # type: ignore[assignment]
        return result

    def stats(self, enable: bool = False, reset: bool = False) -> tuple[int, int]:
        """
        Get cache statistics.

        Parameters:
            enable: Enable statistics tracking
            reset: Reset statistics

        Returns:
            Tuple of (hits, misses)
        """
        result: tuple[int, int] = cast(tuple[int, int], self._cache.stats(enable=enable, reset=reset))  # type: ignore[assignment]
        return result

    def volume(self) -> int:
        """
        Get total size of cache in bytes.

        Returns:
            Size in bytes
        """
        result: int = self._cache.volume()  # type: ignore[assignment]
        return result

    def iterkeys(self, reverse: bool = False) -> Iterator[str]:
        """
        Iterate over cache keys.

        Parameters:
            reverse: Iterate in reverse order

        Returns:
            Iterator of keys
        """
        result: Iterator[str] = self._cache.iterkeys(reverse=reverse)  # type: ignore[assignment]  # pyright: ignore[reportAssignmentType]
        return result

    def __len__(self) -> int:
        """Return the number of items in the cache."""
        length: int = len(self._cache)  # type: ignore[assignment]  # pyright: ignore[reportArgumentType]
        return length

    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache."""
        result: bool = key in self._cache  # type: ignore[assignment]
        return result

    def __iter__(self) -> Iterator[str]:
        """Iterate over cache keys."""
        result: Iterator[str] = iter(self._cache)  # type: ignore[assignment]  # pyright: ignore[reportAssignmentType]
        return result
