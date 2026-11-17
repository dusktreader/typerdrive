"""
Provide commands that can be added to a `typer` app to manage settings.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import import_module
from types import UnionType
from typing import (  # noqa: F401 -- Annotated must be in __globals__ for Python 3.14 lazy annotation eval
    Annotated,
    Any,
    Union,
    get_args,
    get_origin,
)

import typer
from pydantic import BaseModel, SecretStr
from pydantic_core import PydanticUndefined
from typer import Context as Context  # noqa: PLC0414 -- needed for dynamic annotation globals
from typer_repyt.build_command import DecDef, OptDef, build_command
from typer_repyt.constants import Sentinel

from typerdrive.config import get_typerdrive_config
from typerdrive.constants import Validation
from typerdrive.file_ops import atomic_write
from typerdrive.format import pretty_annotation, pretty_model
from typerdrive.handle_errors import handle_errors
from typerdrive.model_parser import is_model_collection, is_model_type, make_parser
from typerdrive.settings.attach import attach_settings, get_settings_manager
from typerdrive.settings.exceptions import SettingsError
from typerdrive.settings.manager import SettingsManager
from typerdrive.settings.secrets.utilities import reset_encrypted_fields


def _secret_cli_type(annotation: Any) -> Any | None:
    if isinstance(annotation, type) and issubclass(annotation, SecretStr):
        return str
    if get_origin(annotation) in (Union, UnionType):
        args = get_args(annotation)
        if len(args) == 2 and type(None) in args:
            secret_type = next(arg for arg in args if arg is not type(None))
            if isinstance(secret_type, type) and issubclass(secret_type, SecretStr):
                return str | None
    return None


def bind(ctx: typer.Context):
    """
    Bind all settings for the app.
    """
    __manager: SettingsManager = get_settings_manager(ctx)
    excluded_locals = ["__manager", "ctx"]
    settings_values = {k: v for (k, v) in locals().items() if k not in excluded_locals}
    __manager.update(**settings_values)


def add_bind(cli: typer.Typer, settings_model: type[BaseModel]):
    """
    Add the `bind` command to the given `typer` app.
    """
    opt_defs: list[OptDef] = []
    for name, field_info in settings_model.model_fields.items():
        default = field_info.default if field_info.default is not PydanticUndefined else Sentinel.NOT_GIVEN
        annotation: Any = SettingsError.enforce_defined(field_info.annotation, "Option type may not be `None`")

        secret_cli_type = _secret_cli_type(annotation)
        is_secret = secret_cli_type is not None
        is_collection = is_model_collection(annotation)
        is_nested_model = is_model_type(annotation)

        opt_kwargs: dict[str, Any] = {
            "name": name,
            "param_type": secret_cli_type if is_secret else str if is_collection else annotation,
            "default": default.get_secret_value() if isinstance(default, SecretStr) else default,
            "help": field_info.description,
            "show_default": not is_secret,
            "hide_input": is_secret,
        }
        if not is_secret and (is_nested_model or is_collection):
            opt_kwargs["parser"] = make_parser(annotation)
            opt_kwargs["metavar"] = pretty_model(annotation) if is_nested_model else pretty_annotation(annotation)

        opt_defs.append(OptDef(**opt_kwargs))
    build_command(
        cli,
        bind,
        *opt_defs,
        decorators=[
            DecDef(
                dec_func=handle_errors,
                dec_args=["Failed to bind settings"],
                dec_kwargs={
                    "handle_exc_class": SettingsError,
                    "unwrap_message": False,
                    "debug": True,
                },
                is_simple=False,
            ),
            DecDef(
                dec_func=attach_settings,
                dec_args=[settings_model],
                dec_kwargs={"validation": Validation.AFTER, "persist": True, "show": True},
                is_simple=False,
            ),
        ],
        include_context=True,
    )


def update(ctx: typer.Context):
    """
    Update some settings for the app.
    """
    __manager: SettingsManager = get_settings_manager(ctx)
    excluded_locals = ["__manager", "ctx"]
    settings_values = {k: v for (k, v) in locals().items() if k not in excluded_locals and v is not None}
    __manager.update(**settings_values)


def add_update(cli: typer.Typer, settings_model: type[BaseModel]):
    """
    Add the `update` command to the given `typer` app.
    """
    opt_defs: list[OptDef] = []
    for name, field_info in settings_model.model_fields.items():
        annotation: Any = SettingsError.enforce_defined(field_info.annotation, "Option type may not be `None`")
        default: None | bool = None
        is_secret = _secret_cli_type(annotation) is not None
        is_collection = is_model_collection(annotation)
        is_nested_model = is_model_type(annotation)
        cli_type = str if is_secret or is_collection else annotation
        opt_kwargs: dict[str, Any] = {
            "name": name,
            "param_type": cli_type | None,
            "default": default,
            "help": field_info.description,
            "show_default": not is_secret,
            "hide_input": is_secret,
        }
        if not is_secret and (is_nested_model or is_collection):
            opt_kwargs["parser"] = make_parser(annotation)
            opt_kwargs["metavar"] = pretty_model(annotation) if is_nested_model else pretty_annotation(annotation)

        opt_defs.append(OptDef(**opt_kwargs))
    build_command(
        cli,
        update,
        *opt_defs,
        decorators=[
            DecDef(
                dec_func=handle_errors,
                dec_args=["Failed to update settings"],
                dec_kwargs={
                    "handle_exc_class": SettingsError,
                    "unwrap_message": False,
                    "debug": True,
                },
                is_simple=False,
            ),
            DecDef(
                dec_func=attach_settings,
                dec_args=[settings_model],
                dec_kwargs={"validation": Validation.NEVER, "persist": True, "show": True},
                is_simple=False,
            ),
        ],
        include_context=True,
    )


def unset(ctx: typer.Context):
    """
    Remove some settings from the app.
    """
    __manager: SettingsManager = get_settings_manager(ctx)
    excluded_locals = ["__manager", "ctx"]
    settings_values = {k: v for (k, v) in locals().items() if k not in excluded_locals and v}
    __manager.unset(*settings_values.keys())


def add_unset(cli: typer.Typer, settings_model: type[BaseModel]):
    """
    Add the `unset` command to the given `typer` app.
    """
    opt_defs: list[OptDef] = []
    for name, field_info in settings_model.model_fields.items():
        opt_defs.append(
            OptDef(
                name=name,
                param_type=bool,
                default=False,
                help=field_info.description,
                show_default=True,
                override_name=name,
            )
        )
    build_command(
        cli,
        unset,
        *opt_defs,
        decorators=[
            DecDef(
                dec_func=handle_errors,
                dec_args=["Failed to unset settings"],
                dec_kwargs={
                    "handle_exc_class": SettingsError,
                    "unwrap_message": False,
                    "debug": True,
                },
                is_simple=False,
            ),
            DecDef(
                dec_func=attach_settings,
                dec_args=[settings_model],
                dec_kwargs={"validation": Validation.NEVER, "persist": True, "show": True},
                is_simple=False,
            ),
        ],
        include_context=True,
    )


def show(ctx: typer.Context):
    """
    Show the current app's settings.
    """


def add_show(cli: typer.Typer, settings_model: type[BaseModel]):
    """
    Add the `show` command to the given `typer` app.
    """
    build_command(
        cli,
        show,
        decorators=[
            DecDef(
                dec_func=handle_errors,
                dec_args=["Failed to show settings"],
                dec_kwargs={
                    "handle_exc_class": SettingsError,
                    "unwrap_message": False,
                    "debug": True,
                },
                is_simple=False,
            ),
            DecDef(
                dec_func=attach_settings,
                dec_args=[settings_model],
                dec_kwargs={"validation": Validation.NEVER, "persist": False, "show": True},
                is_simple=False,
            ),
        ],
        include_context=True,
    )


def reset(ctx: typer.Context):
    """
    Remove all settings from the app.
    """
    typer.confirm("Are you sure you want to reset your settings?", abort=True)
    __manager: SettingsManager = get_settings_manager(ctx)
    __manager.reset()
    try:
        import_module("pyrage")
    except ModuleNotFoundError:
        return
    SecretEncryption, _ = _require_encryption()
    SecretEncryption(get_typerdrive_config()).reset()


def add_reset(cli: typer.Typer, settings_model: type[BaseModel]):
    """
    Add the `reset` command to the given `typer` app.
    """
    build_command(
        cli,
        reset,
        decorators=[
            DecDef(
                dec_func=handle_errors,
                dec_args=["Failed to reset settings"],
                dec_kwargs={
                    "handle_exc_class": SettingsError,
                    "unwrap_message": False,
                    "debug": True,
                },
                is_simple=False,
            ),
            DecDef(
                dec_func=attach_settings,
                dec_args=[settings_model],
                dec_kwargs={"validation": Validation.NEVER, "persist": True, "show": True},
                is_simple=False,
            ),
        ],
        include_context=True,
    )


def _passphrase(prompt: str, *, confirm: bool = False) -> str:
    value = typer.prompt(prompt, default="", show_default=False, hide_input=True)
    if not value:
        typer.echo("Passphrase cannot be empty.", err=True)
        raise typer.Exit(1)
    if confirm:
        confirmation = typer.prompt("Confirm new passphrase", default="", show_default=False, hide_input=True)
        if value != confirmation:
            typer.echo("Passphrases do not match.", err=True)
            raise typer.Exit(1)
    return value


def _contains_age_marker(value: Any) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and item.startswith("age:"):
            return True
        if isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


def _require_encryption() -> tuple[Any, Any]:
    try:
        import_module("pyrage")
    except ModuleNotFoundError as exc:
        if exc.name != "pyrage":
            raise
        typer.echo("Secret encryption requires the typerdrive[encrypt-secrets] extra.", err=True)
        raise typer.Exit(1) from None
    from typerdrive.settings.exceptions import SecretEncryptionError
    from typerdrive.settings.secrets.encryption import SecretEncryption

    return SecretEncryption, SecretEncryptionError


@contextmanager
def _encryption_errors(secret_encryption_error: type[Exception]) -> Iterator[None]:
    try:
        yield
    except secret_encryption_error:
        typer.echo("Encryption operation failed; check the passphrase, key material, and cache permissions.", err=True)
        raise typer.Exit(1) from None
    except OSError:
        typer.echo("Encryption operation failed due to a filesystem error.", err=True)
        raise typer.Exit(1) from None


def encryption_setup(
    no_passphrase: Annotated[
        bool, typer.Option("--no-passphrase", help="Store the identity without passphrase protection.")
    ] = False,
) -> None:
    """Create secret encryption key material."""
    SecretEncryption, secret_encryption_error = _require_encryption()
    with _encryption_errors(secret_encryption_error):
        config = get_typerdrive_config()
        encryption = SecretEncryption(config)
        if encryption.material_path.exists():
            typer.echo("Secret encryption key material already exists; it will not be replaced.", err=True)
            raise typer.Exit(1)
        try:
            settings = json.loads(config.settings_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            settings = None
        except (ValueError, UnicodeError, RecursionError):
            typer.echo("Cannot inspect settings for encrypted secrets; restore or repair the settings file.", err=True)
            raise typer.Exit(1) from None
        if _contains_age_marker(settings):
            typer.echo("Encrypted settings found without key material; restore the original key material.", err=True)
            raise typer.Exit(1)
        encryption.setup(None if no_passphrase else _passphrase("New passphrase", confirm=True))
        if no_passphrase:
            typer.echo("Secret encryption set up; the identity is stored without passphrase protection.")
        else:
            typer.echo("Secret encryption set up.")


def _is_unprotected(encryption: Any) -> bool:
    if not encryption.material_path.exists():
        return False
    return not encryption.is_passphrase_protected


def encryption_change_passphrase() -> None:
    """Change the secret encryption passphrase."""
    SecretEncryption, secret_encryption_error = _require_encryption()
    with _encryption_errors(secret_encryption_error):
        encryption = SecretEncryption(get_typerdrive_config())
        if _is_unprotected(encryption):
            typer.echo("Cannot change the passphrase of an unprotected key; migration is not supported.", err=True)
            raise typer.Exit(1)
        old = _passphrase("Current passphrase")
        new = _passphrase("New passphrase", confirm=True)
        encryption.change_passphrase(old, new)
        typer.echo("Secret encryption passphrase changed.")


def encryption_lock() -> None:
    """Remove the cached secret encryption identity."""
    SecretEncryption, secret_encryption_error = _require_encryption()
    with _encryption_errors(secret_encryption_error):
        SecretEncryption(get_typerdrive_config()).lock()
        typer.echo("Cached identity removed; an unprotected key remains usable without a passphrase.")


def add_encryption_reset(cli: typer.Typer, settings_model: type[BaseModel]):
    """
    Add the `reset` command to the given `encryption` subcommand app.
    """

    def encryption_reset() -> None:
        """Remove the secret encryption identity and reset all encrypted settings values to their defaults."""
        SecretEncryption, secret_encryption_error = _require_encryption()
        with _encryption_errors(secret_encryption_error):
            config = get_typerdrive_config()
            encryption = SecretEncryption(config)
            if not encryption.material_path.exists():
                typer.echo("There is no secret encryption identity to reset.", err=True)
                raise typer.Exit(1)
            typer.confirm(
                "This permanently removes the encryption identity and resets all encrypted settings values to their"
                " defaults. Continue?",
                abort=True,
            )
            try:
                settings = json.loads(config.settings_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                settings = None
            except (ValueError, UnicodeError, RecursionError):
                typer.echo("Cannot read the settings file; restore or repair it before resetting.", err=True)
                raise typer.Exit(1) from None
            if settings is not None:
                content = json.dumps(reset_encrypted_fields(settings_model, settings), indent=2)
                atomic_write(config.settings_path, content.encode("utf-8"))
            encryption.reset()
            typer.echo(
                "Secret encryption identity removed and encrypted settings reset. Run `encryption setup` to start over."
            )

    cli.command("reset")(encryption_reset)


def encryption_unlock() -> None:
    """Unlock the secret encryption identity."""
    SecretEncryption, secret_encryption_error = _require_encryption()
    with _encryption_errors(secret_encryption_error):
        config = get_typerdrive_config()
        encryption = SecretEncryption(config)
        if _is_unprotected(encryption):
            typer.echo("Cannot unlock an unprotected key; it is already usable without a passphrase.", err=True)
            raise typer.Exit(1)
        encryption.unlock(_passphrase("Secret encryption passphrase"))
        if config.encryption_cache_ttl == 0:
            typer.echo("Passphrase verified; identity caching is disabled.")
        else:
            typer.echo("Secret encryption unlocked.")


def add_settings_subcommand(cli: typer.Typer, settings_model: type[BaseModel]):
    """
    Add all `settings` commands to the given app.
    """
    settings_cli = typer.Typer(help="Manage settings for the app", invoke_without_command=True, no_args_is_help=True)

    for cmd in [add_bind, add_update, add_unset, add_reset, add_show]:
        cmd(settings_cli, settings_model)

    encryption_cli = typer.Typer(
        help="Manage encryption of secret settings values", invoke_without_command=True, no_args_is_help=True
    )
    for name, command in [
        ("setup", encryption_setup),
        ("change-passphrase", encryption_change_passphrase),
        ("lock", encryption_lock),
        ("unlock", encryption_unlock),
    ]:
        encryption_cli.command(name)(command)
    add_encryption_reset(encryption_cli, settings_model)
    settings_cli.add_typer(encryption_cli, name="encryption")

    cli.add_typer(settings_cli, name="settings")
