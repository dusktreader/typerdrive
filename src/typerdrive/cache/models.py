"""
Provide data models for cache functionality.
"""

from pydantic import BaseModel, Field


class CacheStats(BaseModel):
    """
    Statistics about the cache.
    """

    hits: int = Field(description="Number of cache hits")
    misses: int = Field(description="Number of cache misses")
    size: int = Field(description="Number of entries in the cache")
    volume: int = Field(description="Total size of cache in bytes")
