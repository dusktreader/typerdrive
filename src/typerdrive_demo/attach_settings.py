"""
This set of demos shows the use of the `attach_settings` decorator.
"""

import typer
from pydantic import BaseModel, ConfigDict
from typerdrive import (
    EncryptedSecretStr,
    PlaintextSecretStr,
    SettingsManager,
    Validation,
    attach_settings,
    get_settings,
)
from typerdrive.config import get_typerdrive_config
from typerdrive.settings.secrets.encryption import SecretEncryption

from typerdrive_demo.helpers import demo


@demo("attach_settings")
def demo_1__attach_settings__basic():
    """
    This function demonstrates the use of the `attach_settings` decorator.
    This decorator allows you to attach a Pydantic model to a typer command.
    The settings are accessed by providing an argument with matching model type.
    Note that the settings argument name can be anything you like.
    In order to use this decorator, your command must take a `typer.Context`
    object as the first argument.
    """

    class ExampleSettings(BaseModel):
        name: str = "jawa"
        planet: str = "tatooine"
        alignment: str = "neutral"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings)
    def report(ctx: typer.Context, cfg: ExampleSettings):
        print(f"Look at this {cfg.name} from {cfg.planet}. It's soooo {cfg.alignment}!")

    cli()


@demo("attach_settings")
def demo_2__attach_settings__enforce_validation():
    """
    This function demonstrates how the `attach_settings` decorator will,
    by default, require the settings to be valid before they can be
    attached to the app's context.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str = "tatooine"
        alignment: str = "neutral"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings)
    def report(ctx: typer.Context, cfg: ExampleSettings):
        print("We will never got to this line")

    cli()


@demo("attach_settings")
def demo_3__attach_settings__allow_invalid():
    """
    This function demonstrates how the `validation` argument passed to the
    `attach_settings` decorator works. By default this flag is set to
    `Validation.BEFORE`, meaning the settings must be valid before it is
    attached to the app's context. If you set it to `Validation.NEVER`, the
    settings will be bound even if there are invalid settings. This is
    important because your settings may have non-default settings that need
    to be set _through_ a command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str = "tatooine"
        alignment: str = "neutral"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings, validation=Validation.NEVER)
    def report(ctx: typer.Context, cfg: ExampleSettings):
        print(f"Here are the settings that are missing a required field: {cfg}")

    cli()


@demo("attach_settings")
def demo_4__attach_settings__access_through_context():
    """
    This function demonstrates how the settings can also be accessed through
    the Typer context if you do not want to use a settings parameter. To access
    settings with the context, use the `get_settings()` helper function.
    """

    class ExampleSettings(BaseModel):
        name: str = "jawa"
        planet: str = "tatooine"
        alignment: str = "neutral"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings)
    def report(ctx: typer.Context):
        cfg = get_settings(ctx, ExampleSettings)
        print(f"Look at this {cfg.name} from {cfg.planet}. It's soooo {cfg.alignment}!")

    cli()


@demo("attach_settings")
def demo_5__attach_settings__with_secrets():
    """
    This function demonstrates how settings are printed when they contain secrets.
    By default, all fields in a Pydantic model that are of type `PlaintextSecretStr`
    will be redacted when the settings are printed to the console. This is to prevent
    sensitive information from being accidentally exposed. However, the actual values of
    the secrets will still be available in the settings object and can be accessed as normal.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        name: str = "yoda"
        planet: PlaintextSecretStr = PlaintextSecretStr("tatooine")
        alignment: str = "good"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings)
    def report(ctx: typer.Context, cfg: ExampleSettings):
        print(f"Look at this {cfg.name} from {cfg.planet}. It's soooo {cfg.alignment}!")

    cli()


@demo("attach_settings", input_lines=["demo-passphrase"])
def demo_6__attach_settings__with_encrypted_secrets():
    """
    This function demonstrates settings that contain an `EncryptedSecretStr`.
    Like a `PlaintextSecretStr`, the value is redacted when the settings are printed. Unlike a `PlaintextSecretStr`, the
    value is also encrypted when the settings are saved, so the settings file never contains the plaintext.
    The value is decrypted lazily, only when `get_secret_value()` is called. If the encryption key is
    protected by a passphrase (as it is here), that call prompts for the passphrase.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        name: str = "yoda"
        api_token: EncryptedSecretStr = EncryptedSecretStr("not-a-real-token")

    SecretEncryption(get_typerdrive_config()).setup("demo-passphrase")
    SettingsManager(ExampleSettings).save()

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings)
    def report(ctx: typer.Context, cfg: ExampleSettings):
        print(f"Settings: {cfg}")
        print(f"The token has {len(cfg.api_token.get_secret_value())} characters.")

    cli()
