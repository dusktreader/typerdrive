import inspect
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Concatenate, ParamSpec, TypeVar, cast

import typer

from typerdrive.async_tools import ensure_sync_context, run_async, run_on_current_sync_adapter
from typerdrive.cloaked import CloakingDevice
from typerdrive.context import TyperdriveContext, from_context, get_user_context, to_context
from typerdrive.database.exceptions import DatabaseError, DatabaseLifecycleError
from typerdrive.database.manager import DatabaseManager
from typerdrive.database.migrations import MigrationRegistry
from typerdrive.database.session import DatabaseSession
from typerdrive.signature import SignatureRewriter

P = ParamSpec("P")
T = TypeVar("T")
ContextFunction = Callable[Concatenate[typer.Context, P], T]


def get_database_manager(ctx: typer.Context) -> DatabaseManager:
    with DatabaseError.handle_errors(
        "Database manager is not bound to the context. Use the @attach_database() decorator"
    ):
        manager: Any = from_context(ctx, "database_manager")
    return DatabaseError.ensure_type(
        manager,
        DatabaseManager,
        "Item in user context at `database_manager` was not a DatabaseManager",
    )


def get_database_session(ctx: typer.Context) -> DatabaseSession:
    with DatabaseError.handle_errors(
        "Database session is not bound to the context. Use the @attach_database() decorator"
    ):
        session: Any = from_context(ctx, "database_session")
    return DatabaseError.ensure_type(
        session,
        DatabaseSession,
        "Item in user context at `database_session` was not a DatabaseSession",
    )


def _bind_manager(ctx: typer.Context, manager: DatabaseManager) -> None:
    to_context(ctx, "database_manager", manager)


def _bind_session(ctx: typer.Context, session: DatabaseSession) -> None:
    to_context(ctx, "database_session", session)


def _clear_database(ctx: typer.Context) -> None:
    context: TyperdriveContext = get_user_context(ctx)
    context.database_manager = None
    context.database_session = None


def attach_database(
    migration_registry: MigrationRegistry | None = None,
    *,
    journal_mode: str = "WAL",
) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
    registry = migration_registry if migration_registry is not None else MigrationRegistry()

    def decorate(func: ContextFunction[P, T]) -> ContextFunction[P, T]:
        manager_param_key: str | None = None
        session_param_key: str | None = None
        rewriter = SignatureRewriter(func)
        for key, hint in rewriter.hints.items():
            if hint is DatabaseManager:
                rewriter.cloak(key, Annotated[DatabaseManager | None, CloakingDevice])
                manager_param_key = key
            elif hint is DatabaseSession:
                rewriter.cloak(key, Annotated[DatabaseSession | None, CloakingDevice])
                session_param_key = key

        if manager_param_key is not None and session_param_key is not None:
            raise DatabaseLifecycleError("A command can inject either DatabaseManager or DatabaseSession, not both")

        if inspect.iscoroutinefunction(func):

            async def invoke_async(ctx: typer.Context, *args: P.args, **kwargs: P.kwargs):
                manager = DatabaseManager(journal_mode=journal_mode)
                _bind_manager(ctx, manager)
                try:
                    async with manager.create_session() as migration_session:
                        await registry.apply(migration_session)
                    if manager_param_key is not None:
                        cast(dict[str, Any], kwargs)[manager_param_key] = manager
                        return await func(ctx, *args, **kwargs)
                    session = manager.create_session()
                    if session_param_key is not None:
                        cast(dict[str, Any], kwargs)[session_param_key] = session
                    async with session:
                        _bind_session(ctx, session)
                        return await func(ctx, *args, **kwargs)
                finally:
                    _clear_database(ctx)

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
                _bind_manager(ctx, manager)
                try:
                    with manager.create_session() as migration_session:
                        run_on_current_sync_adapter(registry.apply, migration_session)
                    if manager_param_key is not None:
                        cast(dict[str, Any], kwargs)[manager_param_key] = manager
                        result = func(ctx, *args, **kwargs)
                        if inspect.isawaitable(result):

                            async def await_result():
                                return await cast(Awaitable[Any], result)

                            return run_async(await_result)
                        return result
                    session = manager.create_session()
                    if session_param_key is not None:
                        cast(dict[str, Any], kwargs)[session_param_key] = session
                    with session:
                        _bind_session(ctx, session)
                        result = func(ctx, *args, **kwargs)
                        if inspect.isawaitable(result):

                            async def await_result():
                                return await cast(Awaitable[Any], result)

                            return run_on_current_sync_adapter(await_result)
                        return result
                finally:
                    _clear_database(ctx)

        rewriter.apply(wrapper)
        return wrapper

    return decorate
