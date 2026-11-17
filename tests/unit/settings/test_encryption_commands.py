import json
import stat
from pathlib import Path
from typing import Any

import pytest
import typer
from pydantic import BaseModel, Field
from pytest_mock import MockerFixture
from typer.testing import CliRunner
from typerdrive.config import get_typerdrive_config, set_typerdrive_config
from typerdrive.settings.commands import add_settings_subcommand
from typerdrive.settings.manager import SettingsManager
from typerdrive.settings.secrets.encryption import SecretEncryption
from typerdrive.settings.secrets.models import EncryptedSecretStr
from typerdrive.settings.secrets.utilities import reset_encrypted_fields

pytest.importorskip("pyrage")


@pytest.fixture
def cli(mocker: MockerFixture) -> typer.Typer:
    class Settings(BaseModel):
        required: str

    mocker.patch("typerdrive.settings.attach.SettingsManager", side_effect=AssertionError("manager initialized"))
    app = typer.Typer()
    add_settings_subcommand(app, Settings)
    return app


@pytest.fixture
def encryption() -> SecretEncryption:
    return SecretEncryption(get_typerdrive_config())


def invoke(runner: CliRunner, cli: typer.Typer, command: str, inputs: str = ""):
    return runner.invoke(cli, ["settings", "encryption", command], input=inputs)


def test_setup_and_lifecycle(runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption):
    old = "old-passphrase-234"
    new = "new-passphrase-567"
    setup = invoke(runner, cli, "setup", f"{old}\n{old}\n")
    assert setup.exit_code == 0, setup.output
    assert "New passphrase" in setup.output
    assert "Confirm new passphrase" in setup.output
    assert old not in setup.output
    assert stat.S_IMODE(encryption.material_path.stat().st_mode) == 0o600
    assert "AGE-SECRET-KEY-" not in encryption.material_path.read_text()
    assert not encryption.cache_path.exists()
    ciphertext = encryption.encrypt("settings-secret-987")
    assert "settings-secret-987" not in ciphertext

    unlock = invoke(runner, cli, "unlock", f"{old}\n")
    assert unlock.exit_code == 0, unlock.output
    assert old not in unlock.output
    assert encryption.cache_path.exists()
    lock = invoke(runner, cli, "lock")
    assert lock.exit_code == 0, lock.output
    assert not encryption.cache_path.exists()

    rotation = invoke(runner, cli, "change-passphrase", f"{old}\n{new}\n{new}\n")
    assert rotation.exit_code == 0, rotation.output
    assert "Current passphrase" in rotation.output
    assert "Confirm new passphrase" in rotation.output
    assert old not in rotation.output and new not in rotation.output
    failed = invoke(runner, cli, "unlock", f"{old}\n")
    assert failed.exit_code != 0
    assert old not in failed.output
    recovered = invoke(runner, cli, "unlock", f"{new}\n")
    assert recovered.exit_code == 0, recovered.output
    assert new not in recovered.output
    assert encryption.decrypt(ciphertext) == "settings-secret-987"


def test_setup_without_passphrase(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption, mocker: MockerFixture
):
    settings_path = encryption.config.settings_path
    settings_path.write_text('{"secret":"plaintext"}')
    original_settings = settings_path.read_bytes()
    prompt = mocker.patch("typer.prompt", side_effect=AssertionError("unexpected prompt"))
    setup = runner.invoke(cli, ["settings", "encryption", "setup", "--no-passphrase"])
    assert setup.exit_code == 0, setup.output
    prompt.assert_not_called()
    assert stat.S_IMODE(encryption.material_path.stat().st_mode) == 0o600
    assert not encryption.cache_path.exists()
    assert settings_path.read_bytes() == original_settings
    material = encryption.material_path.read_bytes()
    ciphertext = encryption.encrypt("settings-secret-987")
    assert ciphertext.startswith("age:")
    assert "settings-secret-987" not in ciphertext
    assert SecretEncryption(encryption.config).decrypt(ciphertext) == "settings-secret-987"
    prompt.assert_not_called()
    assert not encryption.cache_path.exists()
    duplicate = runner.invoke(cli, ["settings", "encryption", "setup", "--no-passphrase"])
    assert duplicate.exit_code != 0
    assert "already exists" in duplicate.output
    assert encryption.material_path.read_bytes() == material
    assert settings_path.read_bytes() == original_settings
    assert not encryption.cache_path.exists()
    prompt.assert_not_called()

    lock = invoke(runner, cli, "lock")
    assert lock.exit_code == 0, lock.output
    assert "remains usable" in lock.output
    assert encryption.decrypt(ciphertext) == "settings-secret-987"
    unlock = invoke(runner, cli, "unlock")
    assert unlock.exit_code != 0
    assert "unprotected" in unlock.output
    rotation = invoke(runner, cli, "change-passphrase")
    assert rotation.exit_code != 0
    assert "migration is not supported" in rotation.output
    assert encryption.material_path.read_bytes() == material
    assert settings_path.read_bytes() == original_settings
    assert not encryption.cache_path.exists()
    prompt.assert_not_called()


def test_setup_rejects_mismatch_empty_and_existing_material(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption
):
    mismatch = invoke(runner, cli, "setup", "private-one\nprivate-two\n")
    assert mismatch.exit_code != 0
    assert "match" in mismatch.output
    assert "private-one" not in mismatch.output and "private-two" not in mismatch.output
    empty = invoke(runner, cli, "setup", "\n")
    assert empty.exit_code != 0
    assert "empty" in empty.output
    assert not encryption.material_path.exists()
    assert invoke(runner, cli, "setup", "original\noriginal\n").exit_code == 0
    material = encryption.material_path.read_bytes()
    duplicate = invoke(runner, cli, "setup", "replacement\nreplacement\n")
    assert duplicate.exit_code != 0
    assert "replacement" not in duplicate.output
    assert encryption.material_path.read_bytes() == material
    duplicate_unprotected = runner.invoke(cli, ["settings", "encryption", "setup", "--no-passphrase"])
    assert duplicate_unprotected.exit_code != 0
    assert encryption.material_path.read_bytes() == material
    assert invoke(runner, cli, "unlock", "original\n").exit_code == 0


@pytest.mark.parametrize("inputs", ["\n", "original\n\n", "original\nnew-value\nother-value\n"])
def test_rotation_rejects_invalid_prompts(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption, inputs: str
):
    encryption.setup("original")
    material = encryption.material_path.read_bytes()
    result = invoke(runner, cli, "change-passphrase", inputs)
    assert result.exit_code != 0
    assert "original" not in result.output and "new-value" not in result.output and "other-value" not in result.output
    assert encryption.material_path.read_bytes() == material
    assert invoke(runner, cli, "unlock", "original\n").exit_code == 0


def test_failed_rotation_and_missing_keys_recover(runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption):
    missing = invoke(runner, cli, "unlock", "sensitive-missing\n")
    assert missing.exit_code != 0
    assert "sensitive-missing" not in missing.output
    assert not encryption.material_path.exists()
    empty = invoke(runner, cli, "unlock", "\n")
    assert empty.exit_code != 0
    assert "empty" in empty.output
    encryption.setup("original")
    material = encryption.material_path.read_bytes()
    failed = invoke(runner, cli, "change-passphrase", "wrong-private\nnew-private\nnew-private\n")
    assert failed.exit_code != 0
    assert "wrong-private" not in failed.output and "new-private" not in failed.output
    assert encryption.material_path.read_bytes() == material
    assert invoke(runner, cli, "unlock", "original\n").exit_code == 0


@pytest.mark.parametrize("value", ["message: hello", "prefix age:private-ciphertext"])
def test_setup_allows_plaintext_with_embedded_age_marker(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption, value: str
):
    path = encryption.config.settings_path
    path.write_text(json.dumps({"message": value}))
    original = path.read_bytes()
    result = runner.invoke(cli, ["settings", "encryption", "setup", "--no-passphrase"])
    assert result.exit_code == 0, result.output
    assert encryption.material_path.exists()
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "settings",
    [
        {"secret": "age:private-ciphertext"},
        {"nested": [{"deep": [None, {"secret": "age:private-ciphertext"}]}]},
        {"age:private-ciphertext": "key"},
    ],
)
@pytest.mark.parametrize("options", [[], ["--no-passphrase"]])
def test_setup_rejects_missing_keys_for_encrypted_settings(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption, settings: Any, options: list[str]
):
    path = encryption.config.settings_path
    path.write_text(json.dumps(settings))
    original = path.read_bytes()
    result = runner.invoke(cli, ["settings", "encryption", "setup", *options], input="private-pass\nprivate-pass\n")
    assert result.exit_code != 0
    assert "restore" in result.output.lower()
    assert "private-ciphertext" not in result.output and "private-pass" not in result.output
    assert not encryption.material_path.exists()
    assert path.read_bytes() == original


@pytest.mark.parametrize("options", [[], ["--no-passphrase"]])
def test_setup_rejects_unreadable_or_invalid_settings(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption, mocker: MockerFixture, options: list[str]
):
    path = encryption.config.settings_path
    path.write_text('{"secret":"private-value",')
    original = path.read_bytes()
    result = runner.invoke(cli, ["settings", "encryption", "setup", *options], input="private-pass\nprivate-pass\n")
    assert result.exit_code != 0
    assert "private-value" not in result.output
    assert not encryption.material_path.exists()
    assert path.read_bytes() == original
    mocker.patch.object(Path, "read_text", side_effect=PermissionError("private-value"))
    result = runner.invoke(cli, ["settings", "encryption", "setup", *options], input="private-pass\nprivate-pass\n")
    assert result.exit_code != 0
    assert "filesystem" in result.output
    assert "private-value" not in result.output
    assert not encryption.material_path.exists()


def test_setup_with_plaintext_settings_and_key_recovery(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption
):
    encryption.setup("original")
    material = encryption.material_path.read_bytes()
    ciphertext = encryption.encrypt("private-secret")
    encryption.material_path.unlink()
    path = encryption.config.settings_path
    path.write_text(json.dumps({"nested": [ciphertext]}))
    failed = invoke(runner, cli, "setup", "different\ndifferent\n")
    assert failed.exit_code != 0
    encryption.material_path.write_bytes(material)
    encryption.material_path.chmod(0o600)
    assert invoke(runner, cli, "unlock", "original\n").exit_code == 0
    assert encryption.decrypt(ciphertext) == "private-secret"
    encryption.material_path.unlink()
    path.write_text(json.dumps({"nested": ["plaintext", 1, None]}))
    assert invoke(runner, cli, "setup", "different\ndifferent\n").exit_code == 0


def test_lock_without_extra(encryption: SecretEncryption, run_without_pyrage):
    encryption.setup("original")
    encryption.unlock("original")
    original_cache = encryption.cache_path.read_bytes()
    run_without_pyrage(
        f"""
import typer
from pydantic import BaseModel, Field
from typer.testing import CliRunner

from typerdrive.config import set_typerdrive_config
from typerdrive.settings.commands import add_settings_subcommand

set_typerdrive_config(
    app_name={encryption.config.app_name!r},
    state_home={str(encryption.config.state_home)!r},
    cache_home={str(encryption.config.cache_home)!r},
)
class Settings(BaseModel):
    value: str = "ordinary"

app = typer.Typer()
add_settings_subcommand(app, Settings)
result = CliRunner().invoke(app, ["settings", "encryption", "lock"])
assert result.exit_code != 0
assert "typerdrive[encrypt-secrets]" in result.output
"""
    )
    assert encryption.cache_path.read_bytes() == original_cache


def test_unlock_without_cache(runner: CliRunner, cli: typer.Typer):
    set_typerdrive_config(encryption_cache_ttl=0)
    encryption = SecretEncryption(get_typerdrive_config())
    encryption.setup("original")
    result = invoke(runner, cli, "unlock", "original\n")
    assert result.exit_code == 0
    assert "caching is disabled" in result.output
    assert "original" not in result.output
    assert not encryption.cache_path.exists()


@pytest.mark.parametrize("options", [[], ["--no-passphrase"]])
def test_missing_extra_is_reported_without_secrets(run_without_pyrage, options: list[str]):
    run_without_pyrage(
        f"""
import typer
from pydantic import BaseModel, Field
from typer.testing import CliRunner

from typerdrive.settings.commands import add_settings_subcommand

class Settings(BaseModel):
    value: str = "private-value"

app = typer.Typer()
add_settings_subcommand(app, Settings)
result = CliRunner().invoke(
    app,
    ["settings", "encryption", "setup", *{options!r}],
    input="private-pass\\nprivate-pass\\n",
)
assert result.exit_code != 0
assert "typerdrive[encrypt-secrets]" in result.output
assert "private-pass" not in result.output and "private-value" not in result.output
"""
    )


@pytest.mark.parametrize(
    "command",
    ["setup", "change-passphrase", "unlock", "lock", "reset"],
)
def test_no_passphrase_options(runner: CliRunner, cli: typer.Typer, command: str):
    result = runner.invoke(cli, ["settings", command, "--passphrase", "value"])
    assert result.exit_code != 0


def test_encryption_reset__removes_identity_and_cache(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption
):
    encryption.setup("a-passphrase-123")
    encryption.unlock("a-passphrase-123")
    assert encryption.material_path.exists()
    assert encryption.cache_path.exists()

    result = invoke(runner, cli, "reset", "y\n")
    assert result.exit_code == 0, result.output
    assert not encryption.material_path.exists()
    assert not encryption.cache_path.exists()

    again = invoke(runner, cli, "setup", "b-passphrase-456\nb-passphrase-456\n")
    assert again.exit_code == 0, again.output


def test_encryption_reset__resets_encrypted_values_to_defaults(runner: CliRunner, encryption: SecretEncryption):
    class Settings(BaseModel):
        name: str = "yoda"
        token: EncryptedSecretStr = EncryptedSecretStr("default-token")

    app = typer.Typer()
    add_settings_subcommand(app, Settings)
    encryption.setup("a-passphrase-123")
    encryption.unlock("a-passphrase-123")
    manager = SettingsManager(Settings)
    manager.update(name="grogu", token="my-secret")
    manager.save()
    assert "age:" in get_typerdrive_config().settings_path.read_text()

    result = runner.invoke(app, ["settings", "encryption", "reset"], input="y\n")
    assert result.exit_code == 0, result.output
    saved = json.loads(get_typerdrive_config().settings_path.read_text())
    assert saved == {"name": "grogu"}
    assert not encryption.material_path.exists()

    encryption.setup(None)
    restored = SettingsManager(Settings).settings_instance
    assert isinstance(restored, Settings)
    assert restored.token.get_secret_value() == "default-token"


def test_encryption_reset__aborts_without_confirmation(
    runner: CliRunner, cli: typer.Typer, encryption: SecretEncryption
):
    encryption.setup("a-passphrase-123")
    result = invoke(runner, cli, "reset", "n\n")
    assert result.exit_code != 0
    assert encryption.material_path.exists()


def test_encryption_reset__fails_without_identity(runner: CliRunner, cli: typer.Typer):
    result = invoke(runner, cli, "reset", "y\n")
    assert result.exit_code == 1
    assert "no secret encryption identity" in result.output


def test_settings_reset__removes_identity(runner: CliRunner, encryption: SecretEncryption):
    class Settings(BaseModel):
        name: str = "yoda"

    app = typer.Typer()
    add_settings_subcommand(app, Settings)
    encryption.setup("a-passphrase-123")
    encryption.unlock("a-passphrase-123")

    result = runner.invoke(app, ["settings", "reset"], input="y\n")
    assert result.exit_code == 0, result.output
    assert not encryption.material_path.exists()
    assert not encryption.cache_path.exists()


def test_encryption_reset__uses_model_fields_not_stored_values(runner: CliRunner, encryption: SecretEncryption):
    class Inner(BaseModel):
        token: EncryptedSecretStr = EncryptedSecretStr("inner-default")
        label: str = "inner"

    class Settings(BaseModel):
        plain: str = "plain-default"
        inner: Inner = Field(default_factory=Inner)
        lookalike: str = "age:not-actually-encrypted"

    app = typer.Typer()
    add_settings_subcommand(app, Settings)
    encryption.setup(None)
    manager = SettingsManager(Settings)
    manager.update(
        plain="kept",
        inner={"token": "inner-secret", "label": "kept-label"},
        lookalike="age:still-a-plain-string",
    )
    manager.save()

    result = runner.invoke(app, ["settings", "encryption", "reset"], input="y\n")
    assert result.exit_code == 0, result.output
    saved = json.loads(get_typerdrive_config().settings_path.read_text())
    assert saved == {"plain": "kept", "inner": {"label": "kept-label"}, "lookalike": "age:still-a-plain-string"}


def test_reset_encrypted_fields__removes_collections_of_encrypted_values():
    class Inner(BaseModel):
        token: EncryptedSecretStr = EncryptedSecretStr("inner-default")

    class Settings(BaseModel):
        tokens: list[EncryptedSecretStr] = []
        by_name: dict[str, EncryptedSecretStr] = {}
        inners: list[Inner] = []
        names: list[str] = []

    data = {
        "tokens": ["age:aaa", "age:bbb"],
        "by_name": {"x": "age:ccc"},
        "inners": [{"token": "age:ddd"}],
        "names": ["age:looks-encrypted-but-is-a-str"],
    }
    assert reset_encrypted_fields(Settings, data) == {
        "inners": [{}],
        "names": ["age:looks-encrypted-but-is-a-str"],
    }
