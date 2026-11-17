"""
This set of demos shows the use of the various settings-related commands.
"""

import json
from pathlib import Path

import typer
from pydantic import BaseModel, ConfigDict
from typerdrive import EncryptedSecretStr, add_settings_subcommand
from typerdrive.config import get_typerdrive_config
from typerdrive.settings.manager import SettingsManager
from typerdrive.settings.secrets.encryption import SecretEncryption

from typerdrive_demo.helpers import demo


@demo("settings_commands")
def demo_01__bind__basic():
    """
    This function demonstrates the use of the `bind` settings command.
    This command allows you to set the settings values for your app as
    defined in the settings model. It will allow you to override
    defaults. After updating the settings model, the updated values are
    written to disk where they can be retrieved for future commands.
    After the `bind` command is complete, it shows the updated settings.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "bind", "--name=jawa", "--planet=tatooine"])


@demo("settings_commands")
def demo_02__bind__invalid_settings():
    """
    This function demonstrates how the `bind` settings command
    requires all settings that do not have a default to be provided
    a value through the command line. If any of these required values
    are not included, the CLI app will show an error message.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "bind", "--name=jawa"])


@demo("settings_commands")
def demo_03__bind__help():
    """
    This function demonstrates the help text that's provided with
    the `bind` command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "bind", "--help"])


@demo("settings_commands")
def demo_04__update():
    """
    This function demonstrates the use of the `update` settings command.
    This command allows you to set _some_ of the settings values for your
    app as defined in the settings model. Unlike the `bind` command,
    `update` allows the settings to have missing values that result in an
    invalid state. Any settings options that are not provided are ignored.
    After the `update` command is complete, it shows the updated settings
    including any settings values that are still invalid.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "update", "--planet=tatooine"])


@demo("settings_commands")
def demo_05__update__help():
    """
    This function demonstrates the help text that's provided with
    the `update` command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "update", "--help"])


@demo("settings_commands")
def demo_06__unset():
    """
    This function demonstrates the use of the `unset` settings command.
    This command allows you to return settings values to their defaults.
    If a selected settings value does not have a default, it will just
    be removed from the settings. The `unset` command allows the final
    settings to be in an invalid state. After the `unset` command is
    complete, it shows the updated settings including any settings
    values that are still invalid.

    Note:
        To demonstrate this working, we need to hack the settings file
        before the command is invoked.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    settings_path = Path.home() / ".local/share/demo_06__unset/settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "name": "hutt",
                "planet": "nal hutta",
                "is_humanoid": False,
                "alignment": "evil",
            },
        ),
    )

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "unset", "--name", "--alignment"])


@demo("settings_commands")
def demo_07__unset__help():
    """
    This function demonstrates the help text that's provided with
    the `unset` command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "unset", "--help"])


@demo("settings_commands")
def demo_08__show():
    """
    This function demonstrates the `show` command. It simply shows
    the current settings.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "show"])


@demo("settings_commands", input_lines=["y"])
def demo_09__reset():
    """
    This function demonstrates the `reset` command. It clears all the
    settings. All settings values with defaults are reset to their
    defaults. All settings values without defaults are just removed.
    After the `reset` command is complete, it shows the updated settings
    including any settings values that are now invalid.

    Note:
        To demonstrate this working, we need to hack the settings file
        before the command is invoked. We also need to add a forced
        confirmation because this command requires you to confirm before
        it proceeds.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    settings_path = Path.home() / ".local/share/demo_09__reset/settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "name": "hutt",
                "planet": "nal hutta",
                "is_humanoid": False,
                "alignment": "evil",
            },
        ),
    )

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "reset"])


@demo("settings_commands")
def demo_10__bind__nested():
    """
    This function demonstrates the use of the `bind` settings command
    with a settings model that includes a nested pydantic model.
    If a nested model is used, the `bind` (and `update`) command will
    parse JSON for the nested settings value
    """

    class ColorModel(BaseModel):
        eyes: str
        hair: str

    class Planet(BaseModel):
        name: str
        climate: str

    class ExampleSettings(BaseModel):
        name: str
        planet: Planet
        coloration: ColorModel
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(
        [
            "settings",
            "bind",
            "--name=jawa",
            """--coloration={"eyes": "yellow", "hair": "black"}""",
            """--planet={"name": "tatooine", "climate": "desert"}""",
        ]
    )


@demo("settings_commands", input_lines=["demo-passphrase", "demo-passphrase"])
def demo_11__encryption_setup():
    """
    This function demonstrates the use of the `encryption setup` settings command.
    This command creates the encryption material that is needed to save any field
    of type `EncryptedSecretStr`. By default, the private key is protected by a
    passphrase that you enter (and confirm) at a hidden prompt. Setup will refuse
    to replace encryption material that already exists.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        api_token: EncryptedSecretStr

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "encryption", "setup"])


@demo("settings_commands")
def demo_12__encryption_setup__no_passphrase():
    """
    This function demonstrates the `--no-passphrase` option of the `encryption setup`
    settings command. This creates a private key that is not protected by a passphrase,
    so saving and decrypting secrets never prompts. The tradeoff is that anyone who can
    read the key file can decrypt your secrets, and locking cannot protect it. The key
    file is only readable by the current user.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        api_token: EncryptedSecretStr

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "encryption", "setup", "--no-passphrase"])


@demo("settings_commands", input_lines=["demo-passphrase"])
def demo_13__encryption_unlock():
    """
    This function demonstrates the use of the `encryption unlock` settings command.
    This command asks for the passphrase of a passphrase-protected key, verifies it, and
    caches the unlocked key for a limited time (`encryption_cache_ttl`, 300 seconds by
    default). While the cache is valid, saving and decrypting secrets will not prompt.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        api_token: EncryptedSecretStr

    SecretEncryption(get_typerdrive_config()).setup("demo-passphrase")
    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "encryption", "unlock"])


@demo("settings_commands")
def demo_14__encryption_lock():
    """
    This function demonstrates the use of the `encryption lock` settings command.
    This command removes the cached unlocked key, so the next save or decryption
    of a secret will prompt for the passphrase again.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        api_token: EncryptedSecretStr

    encryption = SecretEncryption(get_typerdrive_config())
    encryption.setup("demo-passphrase")
    encryption.unlock("demo-passphrase")
    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "encryption", "lock"])


@demo("settings_commands", input_lines=["demo-passphrase", "demo-new-passphrase", "demo-new-passphrase"])
def demo_15__encryption_change_passphrase():
    """
    This function demonstrates the use of the `encryption change-passphrase` settings command.
    This command asks for the current passphrase, then for a new passphrase (and a confirmation),
    and protects the private key with the new one. Your saved secrets are not re-encrypted,
    so they do not change. This is only possible for passphrase-protected keys.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        api_token: EncryptedSecretStr

    SecretEncryption(get_typerdrive_config()).setup("demo-passphrase")
    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "encryption", "change-passphrase"])


@demo("settings_commands", input_lines=["y"])
def demo_16__encryption_reset():
    """
    This function demonstrates the use of the `encryption reset` settings command.
    This command is for starting over, for example if you lose your passphrase. After asking for
    confirmation, it permanently removes the encryption key (and any cached copy of it) and resets every
    encrypted settings value back to its default. Other settings are left alone. Afterward, you can
    run `encryption setup` again to create a new key.
    """

    class ExampleSettings(BaseModel):
        model_config = ConfigDict(validate_default=True)

        name: str = "yoda"
        api_token: EncryptedSecretStr = EncryptedSecretStr("default-token")

    encryption = SecretEncryption(get_typerdrive_config())
    encryption.setup("demo-passphrase")
    encryption.unlock("demo-passphrase")
    manager = SettingsManager(ExampleSettings)
    manager.update(name="grogu", api_token="my-secret-token")
    manager.save()

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "encryption", "reset"], standalone_mode=False)

    print("Settings file after reset:")
    print(get_typerdrive_config().settings_path.read_text())
