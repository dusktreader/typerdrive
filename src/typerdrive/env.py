"""
Provide utility functions for working with the environment.
"""

import os
from contextlib import contextmanager


@contextmanager
def tweak_env(**kwargs: str):
    """
    Temporarily alter environment variables for the lifetime of the context manager.

    All items in `kwargs` will be set in the environment.
    If there was exiting value in the given key, it will be restored after the context manager exits.
    If there was no existing value in the given key, it will have no value after the context manager exits.
    """
    old_vals: dict[str, str] = {}
    del_vals: list[str] = []
    for key, val in kwargs.items():
        old_val = os.environ.get(key, None)
        if old_val:
            old_vals[key] = old_val
        else:
            del_vals.append(key)
        os.environ[key] = val

    yield

    for key, val in old_vals.items():
        os.environ[key] = val
    for key in del_vals:
        del os.environ[key]
