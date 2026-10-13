from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar, Token
from typing import Any, Generic, TypeVar

import anyio
from anyio.from_thread import BlockingPortal as AnyIOBlockingPortal
from anyio.from_thread import start_blocking_portal


T = TypeVar("T")
R = TypeVar("R")
AsyncCallable = Callable[..., Awaitable[T]]
AsyncContextManagerFactory = Callable[[], AbstractAsyncContextManager[T]]


class AsyncBridgeError(RuntimeError):
    pass


_current_sync_adapter: ContextVar[BlockingAsyncAdapter[Any] | None] = ContextVar("current_sync_adapter", default=None)


def ensure_sync_context(running_loop_error: Callable[[], Exception] | None = None) -> None:
    try:
        anyio.get_current_task()
    except RuntimeError:
        return
    if running_loop_error is not None:
        raise running_loop_error()
    raise AsyncBridgeError("Synchronous calls cannot run inside an event loop; use the async API")


def current_sync_adapter() -> BlockingAsyncAdapter[Any] | None:
    return _current_sync_adapter.get()


class BlockingAsyncAdapter(AbstractContextManager[T], Generic[T]):
    def __init__(self, context_manager_factory: AsyncContextManagerFactory[T]) -> None:
        self._context_manager_factory = context_manager_factory
        self._portal_context: AbstractContextManager[AnyIOBlockingPortal] | None = None
        self._portal: AnyIOBlockingPortal | None = None
        self._async_context_manager: AbstractAsyncContextManager[T] | None = None
        self._adapter_context_token: Token[BlockingAsyncAdapter[Any] | None] | None = None

    def __enter__(self) -> T:
        ensure_sync_context()
        if self._portal is not None:
            raise AsyncBridgeError("Blocking async adapter is already running")
        portal_context = start_blocking_portal()
        self._portal = portal_context.__enter__()
        self._portal_context = portal_context
        self._adapter_context_token = _current_sync_adapter.set(self)
        try:
            self._async_context_manager = self._context_manager_factory()
            value = self.run(self._async_context_manager.__aenter__)
        except BaseException:
            self._async_context_manager = None
            self._close_portal()
            raise
        return value

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool | None:
        ensure_sync_context()
        context_manager = self._async_context_manager
        if context_manager is None:
            raise AsyncBridgeError("Blocking async adapter is not running")
        try:
            return self.run(context_manager.__aexit__, exc_type, exc_value, traceback)
        finally:
            self._async_context_manager = None
            self._close_portal()

    def run(self, async_callable: AsyncCallable[R], *args: Any, **kwargs: Any) -> R:
        ensure_sync_context()
        portal = self._portal
        if portal is None:
            raise AsyncBridgeError("Blocking async adapter is not running")

        async def invoke() -> R:
            adapter_token = _current_sync_adapter.set(self)
            try:
                return await async_callable(*args, **kwargs)
            finally:
                _current_sync_adapter.reset(adapter_token)

        return portal.call(invoke)

    def _close_portal(self) -> None:
        portal_context = self._portal_context
        adapter_context_token = self._adapter_context_token
        self._portal_context = None
        self._portal = None
        self._adapter_context_token = None
        try:
            if portal_context is not None:
                portal_context.__exit__(None, None, None)
        finally:
            if adapter_context_token is not None:
                _current_sync_adapter.reset(adapter_context_token)


def run_on_current_sync_adapter(async_callable: AsyncCallable[T], *args: Any, **kwargs: Any) -> T:
    adapter = current_sync_adapter()
    if adapter is None:
        raise AsyncBridgeError("No blocking async adapter is active in this context")
    return adapter.run(async_callable, *args, **kwargs)


def run_async(
    async_callable: AsyncCallable[T],
    *args: Any,
    running_loop_error: Callable[[], Exception] | None = None,
    **kwargs: Any,
) -> T:
    ensure_sync_context(running_loop_error)

    async def invoke() -> T:
        return await async_callable(*args, **kwargs)

    return anyio.run(invoke)
