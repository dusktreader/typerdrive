import inspect
from collections.abc import Callable
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar, cast

import typer

from typerdrive.async_tools import ensure_sync_context, run_async, run_on_current_sync_adapter
from typerdrive.cloaked import CloakingDevice
from typerdrive.context import TyperdriveContext, from_context, get_user_context, to_context
from typerdrive.database.exceptions import DatabaseError, DatabaseLifecycleError
from typerdrive.database.manager import DatabaseManager
from typerdrive.database.migrations import MigrationRegistry
from typerdrive.signature import SignatureRewriter


P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def get_database_manager(ctx: typer.Context) -> DatabaseManager:
    with DatabaseError.handle_errors("Database is not bound to the context. Use the @attach_database() decorator"):
        manager: Any = from_context(ctx, "database_manager")
    return DatabaseError.ensure_type(
        manager,
        DatabaseManager,
        "Item in user context at `database_manager` was not a DatabaseManager",
    )


def _bind_manager(ctx: typer.Context, manager: DatabaseManager) -> None:
    to_context(ctx, "database_manager", manager)


def _clear_manager(ctx: typer.Context) -> None:
    context: TyperdriveContext = get_user_context(ctx)
    context.database_manager = None


def attach_database(
    migration_registry: MigrationRegistry | None = None,
    *,
    journal_mode: str = "WAL",
) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    registry = migration_registry if migration_registry is not None else MigrationRegistry()

    def decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        manager_param_key: str | None = None
        rewriter = SignatureRewriter(func)
        for key, hint in rewriter.hints.items():
            if hint is DatabaseManager:
                rewriter.cloak(key, Annotated[DatabaseManager | None, CloakingDevice])
                manager_param_key = key

        if inspect.iscoroutinefunction(func):

            async def invoke_async(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs):
                manager = DatabaseManager(journal_mode=journal_mode)
                _bind_manager(ctx, manager)
                if manager_param_key is not None:
                    cast(dict[str, Any], kwargs)[manager_param_key] = manager
                try:
                    async with manager:
                        try:
                            await registry.apply(manager)
                            return await func(ctx, *args, **kwargs)
                        finally:
                            _clear_manager(ctx)
                except BaseException:
                    if get_user_context(ctx).database_manager is not None:
                        _clear_manager(ctx)
                    raise

            def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs):
                return run_async(
                    invoke_async,
                    ctx,
                    *args,
                    running_loop_error=lambda: DatabaseLifecycleError(
                        "The synchronous Typer command boundary cannot run inside an event loop; "
                        "invoke the command synchronously"
                    ),
                    **kwargs,
                )
        else:

            def wrapper(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs):
                ensure_sync_context(
                    lambda: DatabaseLifecycleError(
                        "The synchronous Typer command boundary cannot run inside an event loop; "
                        "invoke the command synchronously"
                    )
                )
                manager = DatabaseManager(journal_mode=journal_mode)
                if manager_param_key is not None:
                    cast(dict[str, Any], kwargs)[manager_param_key] = manager
                try:
                    with manager:
                        _bind_manager(ctx, manager)
                        try:
                            run_on_current_sync_adapter(registry.apply, manager)
                            result = func(ctx, *args, **kwargs)
                            if inspect.isawaitable(result):

                                async def await_result():
                                    return await result

                                return run_on_current_sync_adapter(await_result)
                            return result
                        finally:
                            _clear_manager(ctx)
                except BaseException:
                    if get_user_context(ctx).database_manager is not None:
                        _clear_manager(ctx)
                    raise

        rewriter.apply(wrapper)
        return wrapper

    return decorate
