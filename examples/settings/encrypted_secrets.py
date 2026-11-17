import typer
from pydantic import BaseModel, ConfigDict
from typerdrive import (
    EncryptedSecretStr,
    PlaintextSecretStr,
    SettingsManager,
    Validation,
    add_settings_subcommand,
    attach_settings,
    set_typerdrive_config,
)


class AppSettings(BaseModel):
    model_config = ConfigDict(validate_default=True)

    api_token: EncryptedSecretStr


cli = typer.Typer()
add_settings_subcommand(cli, AppSettings)


@cli.command()
@attach_settings(AppSettings, validation=Validation.NEVER)
def set_token(ctx: typer.Context, manager: SettingsManager):
    token = typer.prompt("API token", hide_input=True)
    manager.update(api_token=PlaintextSecretStr(token))
    manager.validate()
    manager.save()
    typer.echo("API token saved encrypted.")


@cli.command()
@attach_settings(AppSettings)
def use_token(ctx: typer.Context, settings: AppSettings):
    token = settings.api_token.get_secret_value()
    typer.echo("API token is ready to use." if token else "API token is empty.")


def configure():
    set_typerdrive_config(app_name="settings-encrypted-secrets-example", encryption_cache_ttl=300)


if __name__ == "__main__":
    configure()
    cli()
