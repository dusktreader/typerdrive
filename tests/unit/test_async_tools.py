import asyncio
import threading
from contextlib import asynccontextmanager
from contextvars import ContextVar

import pytest

from typerdrive.async_tools import (
    AsyncBridgeError,
    BlockingAsyncAdapter,
    current_sync_adapter,
    run_async,
    run_on_current_sync_adapter,
)


class TestBlockingAsyncAdapter:
    def test_controls_async_context_manager_entry_and_exit(self):
        events = []

        @asynccontextmanager
        async def resource():
            events.append("entered")
            try:
                yield "resource"
            finally:
                events.append("exited")

        adapter = BlockingAsyncAdapter(resource)
        with adapter as value:
            assert value == "resource"
            assert events == ["entered"]
        assert events == ["entered", "exited"]

    def test_async_context_manager_receives_exception_and_adapter_cleans_up(self):
        events = []

        @asynccontextmanager
        async def resource():
            try:
                yield None
            except ValueError as error:
                events.append(str(error))
                raise

        adapter = BlockingAsyncAdapter(resource)
        with pytest.raises(ValueError, match="body failed"):
            with adapter:
                raise ValueError("body failed")

        assert events == ["body failed"]
        assert current_sync_adapter() is None

    def test_entry_failure_cleans_up_adapter(self):
        @asynccontextmanager
        async def resource():
            raise ValueError("entry failed")
            yield None

        adapter = BlockingAsyncAdapter(resource)
        with pytest.raises(ValueError, match="entry failed"):
            adapter.__enter__()

        assert current_sync_adapter() is None

        async def get_value():
            return 42

        with pytest.raises(AsyncBridgeError, match="not running"):
            adapter.run(get_value)

    def test_propagates_context_and_runs_in_portal_thread(self):
        context_value = ContextVar("context_value", default="missing")
        context_value.set("caller context")
        caller_thread = threading.get_ident()

        @asynccontextmanager
        async def resource():
            yield None

        adapter = BlockingAsyncAdapter(resource)
        with adapter:

            async def inspect_context():
                return context_value.get(), threading.get_ident(), current_sync_adapter()

            value, portal_thread, current_adapter = adapter.run(inspect_context)

        assert value == "caller context"
        assert portal_thread != caller_thread
        assert current_adapter is adapter

    def test_current_adapter_helper_runs_and_cleans_up(self):
        @asynccontextmanager
        async def resource():
            yield None

        adapter = BlockingAsyncAdapter(resource)

        async def get_value():
            return 42

        with adapter:
            assert current_sync_adapter() is adapter
            assert run_on_current_sync_adapter(get_value) == 42

        assert current_sync_adapter() is None
        with pytest.raises(AsyncBridgeError, match="No blocking async adapter"):
            run_on_current_sync_adapter(get_value)

    def test_run_propagates_exceptions(self):
        @asynccontextmanager
        async def resource():
            yield None

        adapter = BlockingAsyncAdapter(resource)
        expected_error = ValueError("operation failed")

        async def fail():
            raise expected_error

        with adapter:
            with pytest.raises(ValueError) as error:
                adapter.run(fail)

        assert error.value is expected_error

    def test_lifecycle_rejects_running_event_loop(self):
        @asynccontextmanager
        async def resource():
            yield None

        adapter = BlockingAsyncAdapter(resource)

        async def start_scenario():
            with pytest.raises(AsyncBridgeError, match="inside an event loop"):
                adapter.__enter__()

        asyncio.run(start_scenario())
        with adapter:

            async def exit_scenario():
                with pytest.raises(AsyncBridgeError, match="inside an event loop"):
                    adapter.__exit__(None, None, None)

            asyncio.run(exit_scenario())

    def test_run_rejects_running_event_loop(self):
        @asynccontextmanager
        async def resource():
            yield None

        adapter = BlockingAsyncAdapter(resource)
        with adapter:

            async def scenario():
                async def get_value():
                    return 42

                with pytest.raises(AsyncBridgeError, match="inside an event loop"):
                    adapter.run(get_value)

            asyncio.run(scenario())


class TestRunAsync:
    def test_runs_async_callable_at_sync_boundary(self):
        async def get_value(value):
            await asyncio.sleep(0)
            return value

        assert run_async(get_value, 42) == 42

    def test_rejects_running_event_loop_with_custom_error(self):
        async def get_value():
            return 42

        async def scenario():
            with pytest.raises(ValueError, match="CLI boundary"):
                run_async(get_value, running_loop_error=lambda: ValueError("CLI boundary"))

        asyncio.run(scenario())
