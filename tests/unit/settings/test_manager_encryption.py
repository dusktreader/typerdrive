import base64
import gc
import json
import weakref
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator
from pytest_mock import MockerFixture
from typerdrive import EncryptedSecretStr, PlaintextSecretStr
from typerdrive.config import TyperdriveConfig
from typerdrive.settings.exceptions import SecretEncryptionError, SettingsSaveError
from typerdrive.settings.manager import SettingsManager
from typerdrive.settings.secrets.encryption import SecretEncryption

pytest.importorskip("pyrage")


class EncryptionConfig(TyperdriveConfig):
    encryption_cache_ttl: int = 0


class Child(BaseModel):
    token: EncryptedSecretStr
    text: str = "age:ordinary"


class Settings(BaseModel):
    secret: EncryptedSecretStr = EncryptedSecretStr("default secret")
    optional: EncryptedSecretStr | None = None
    union: EncryptedSecretStr | int = 4
    child: Child = Child.model_construct(token=EncryptedSecretStr("child secret"))
    items: list[EncryptedSecretStr] = [EncryptedSecretStr("list secret")]
    mapping: dict[str, EncryptedSecretStr] = {"key": EncryptedSecretStr("map secret")}
    tupled: tuple[EncryptedSecretStr, int] = (EncryptedSecretStr("tuple secret"), 2)
    ordinary: PlaintextSecretStr = PlaintextSecretStr("ordinary secret")
    label: str = "original"


@pytest.fixture
def encryption(tmp_path: Path, mocker: MockerFixture) -> SecretEncryption:
    config = EncryptionConfig(app_name="test", state_home=tmp_path / "state", cache_home=tmp_path / "cache")
    mocker.patch("typerdrive.settings.manager.get_typerdrive_config", return_value=config)
    mocker.patch("typerdrive.settings.secrets.encryption.get_typerdrive_config", return_value=config)
    backend = SecretEncryption(config)
    backend.setup("passphrase")
    mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    return backend


def test_public_encrypted_secret_declaration_uses_manager_context(encryption: SecretEncryption):
    class UserSettings(BaseModel):
        secret: EncryptedSecretStr = EncryptedSecretStr("plaintext")

    declared = UserSettings()
    assert declared.model_dump(mode="json") == {"secret": "**********"}

    manager = SettingsManager(UserSettings)
    manager.save()
    saved = json.loads(manager.settings_path.read_text())
    assert saved["secret"].startswith("age:")
    assert "plaintext" not in manager.settings_path.read_text()


@pytest.mark.parametrize("incomplete", [False, True])
def test_encrypted_secret_unions_preserve_plain_containers(encryption: SecretEncryption, incomplete: bool):
    class UnionSettings(BaseModel):
        required: int
        list_or_secret: EncryptedSecretStr | list[str] = ["ordinary"]
        dict_or_secret: EncryptedSecretStr | dict[str, str] = {"key": "ordinary"}
        optional_list_or_secret: EncryptedSecretStr | list[str] | None = None
        optional_secret: EncryptedSecretStr | None = EncryptedSecretStr("optional private")
        secret: EncryptedSecretStr = EncryptedSecretStr("private")

    if not incomplete:
        encryption.config.settings_path.write_text(
            json.dumps(
                {
                    "required": 1,
                    "list_or_secret": ["loaded"],
                    "dict_or_secret": {"loaded": "ordinary"},
                    "optional_list_or_secret": ["optional"],
                }
            )
        )

    manager = SettingsManager(UnionSettings)
    instance = cast(UnionSettings, manager.settings_instance)

    assert instance.list_or_secret == (["ordinary"] if incomplete else ["loaded"])
    assert instance.dict_or_secret == ({"key": "ordinary"} if incomplete else {"loaded": "ordinary"})
    assert instance.optional_list_or_secret == (["optional"] if not incomplete else None)
    assert isinstance(instance.optional_secret, EncryptedSecretStr)
    assert isinstance(instance.secret, EncryptedSecretStr)
    assert bool(manager.invalid_warnings) is incomplete

    manager.save()
    saved = json.loads(manager.settings_path.read_text())
    assert saved["secret"].startswith("age:")
    assert saved["optional_secret"].startswith("age:")
    assert saved["list_or_secret"] == instance.list_or_secret
    assert saved["dict_or_secret"] == instance.dict_or_secret


@pytest.mark.parametrize("invalid_sibling", [False, True])
def test_encrypted_secret_unions_preserve_model_alternatives(encryption: SecretEncryption, invalid_sibling: bool):
    class Child(BaseModel):
        secret: EncryptedSecretStr

    class UnionSettings(BaseModel):
        sibling: int
        child_or_secret: EncryptedSecretStr | Child
        children_or_secret: EncryptedSecretStr | list[Child]
        encrypted_or_child: EncryptedSecretStr | Child

    encryption.config.settings_path.write_text(
        json.dumps(
            {
                "sibling": "invalid" if invalid_sibling else 1,
                "child_or_secret": {"secret": "child secret"},
                "children_or_secret": [{"secret": "list child secret"}],
                "encrypted_or_child": "union secret",
            }
        )
    )

    manager = SettingsManager(UnionSettings)
    instance = cast(UnionSettings, manager.settings_instance)

    assert isinstance(instance.child_or_secret, Child)
    assert isinstance(instance.children_or_secret, list)
    assert isinstance(instance.children_or_secret[0], Child)
    assert isinstance(instance.encrypted_or_child, EncryptedSecretStr)
    assert bool(manager.invalid_warnings) is invalid_sibling

    manager.save()
    saved = json.loads(manager.settings_path.read_text())
    assert saved["child_or_secret"]["secret"].startswith("age:")
    assert saved["children_or_secret"][0]["secret"].startswith("age:")
    assert saved["encrypted_or_child"].startswith("age:")


def test_mixed_secret_fields_persist_only_explicit_encrypted_type(encryption: SecretEncryption):
    class MixedSettings(BaseModel):
        encrypted: EncryptedSecretStr = EncryptedSecretStr("private value")
        ordinary: PlaintextSecretStr = PlaintextSecretStr("ordinary value")

    manager = SettingsManager(MixedSettings)
    manager.save()
    saved = json.loads(manager.settings_path.read_text())

    assert saved["encrypted"].startswith("age:")
    assert saved["ordinary"] == "ordinary value"
    assert "private value" not in manager.settings_path.read_text()


def test_encrypted_secret_plaintext_and_ciphertext_input(encryption: SecretEncryption, mocker: MockerFixture):
    class UserSettings(BaseModel):
        secret: EncryptedSecretStr = EncryptedSecretStr("initial")

    manager = SettingsManager(UserSettings)
    manager.update(secret="updated plaintext")
    manager.save()
    ciphertext = json.loads(manager.settings_path.read_text())["secret"]
    assert ciphertext.startswith("age:")
    assert encryption.decrypt(ciphertext) == "updated plaintext"

    manager.settings_path.write_text(json.dumps({"secret": ciphertext}))
    mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    reloaded = SettingsManager(UserSettings)
    assert cast(UserSettings, reloaded.settings_instance).secret.get_secret_value() == "updated plaintext"


def test_encrypted_secret_without_key_material_preserves_existing_file(encryption: SecretEncryption):
    class UserSettings(BaseModel):
        secret: EncryptedSecretStr = EncryptedSecretStr("private value")

    encryption.config.settings_path.write_text('{"previous": true}')
    manager = SettingsManager(UserSettings)
    original = manager.settings_path.read_bytes()
    encryption.material_path.unlink()

    with pytest.raises(SettingsSaveError, match="material"):
        manager.save()

    assert manager.settings_path.read_bytes() == original


def test_plain_secret_fields_do_not_request_encryption_context(encryption: SecretEncryption, mocker: MockerFixture):
    class PlainSettings(BaseModel):
        secret: PlaintextSecretStr = PlaintextSecretStr("ordinary value")

    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    manager = SettingsManager(PlainSettings)
    manager.save()

    assert json.loads(manager.settings_path.read_text()) == {"secret": "ordinary value"}
    prompt.assert_not_called()


def test_plain_secret_settings_save_without_key_material(tmp_path: Path, mocker: MockerFixture):
    config = TyperdriveConfig(app_name="plaintext", state_home=tmp_path / "state", cache_home=tmp_path / "cache")
    mocker.patch("typerdrive.settings.manager.get_typerdrive_config", return_value=config)
    mocker.patch("typerdrive.settings.secrets.encryption.get_typerdrive_config", return_value=config)
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")

    class PlainSettings(BaseModel):
        secret: PlaintextSecretStr = PlaintextSecretStr("ordinary value")

    manager = SettingsManager(PlainSettings)
    manager.save()

    assert not (config.settings_path.parent / "secret-encryption.json").exists()
    assert json.loads(manager.settings_path.read_text()) == {"secret": "ordinary value"}
    prompt.assert_not_called()


def test_lazy_round_trip_and_update_cache_unlock(encryption: SecretEncryption, mocker: MockerFixture):
    cast(EncryptionConfig, encryption.config).encryption_cache_ttl = 60
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    manager = SettingsManager(Settings)
    manager.update(optional="optional secret", union="union secret")
    manager.save()
    data = json.loads(manager.settings_path.read_text())
    for value in (
        data["secret"],
        data["optional"],
        data["union"],
        data["child"]["token"],
        data["items"][0],
        data["mapping"]["key"],
        data["tupled"][0],
    ):
        assert value.startswith("age:")
    assert data["child"]["text"] == "age:ordinary"
    assert data["ordinary"] == "ordinary secret"
    settings_text = manager.settings_path.read_text()
    assert all(
        plaintext not in settings_text
        for plaintext in (
            "default secret",
            "optional secret",
            "union secret",
            "child secret",
            "list secret",
            "map secret",
            "tuple secret",
        )
    )
    reloaded = SettingsManager(Settings)
    dumped = reloaded.to_dict()
    assert Settings.model_validate(dumped).secret.get_secret_value() == "default secret"
    reloaded.update(label="changed")
    reloaded.unset("label")
    reloaded.save()
    assert json.loads(reloaded.settings_path.read_text())["secret"] == data["secret"]
    prompt.assert_called_once_with("Secret encryption passphrase", hide_input=True)
    instance = cast(Settings, reloaded.settings_instance)
    assert instance.secret.get_secret_value() == "default secret"
    assert instance.optional is not None and instance.optional.get_secret_value() == "optional secret"
    assert instance.child.token.get_secret_value() == "child secret"
    assert instance.items[0].get_secret_value() == "list secret"
    assert instance.mapping["key"].get_secret_value() == "map secret"
    assert instance.tupled[0].get_secret_value() == "tuple secret"
    assert prompt.call_count == 1


def test_encrypted_secret_rejects_grease_stanza_on_decryption(encryption: SecretEncryption):
    ciphertext = encryption.encrypt("secret")
    data = base64.b64decode(ciphertext[4:]).replace(b"--- ", b"-> test-grease\n\n--- ", 1)
    encryption.config.settings_path.write_text(json.dumps({"secret": "age:" + base64.b64encode(data).decode()}))
    manager = SettingsManager(Settings)

    with pytest.raises(SecretEncryptionError, match="decrypt"):
        cast(Settings, manager.settings_instance).secret.get_secret_value()


def test_encrypted_save_is_private_and_atomic(encryption: SecretEncryption, mocker: MockerFixture):
    manager = SettingsManager(Settings)
    manager.save()
    assert manager.settings_path.stat().st_mode & 0o777 == 0o600
    original = manager.settings_path.read_bytes()
    mocker.patch("typerdrive.file_ops.os.replace", side_effect=OSError("failed"))
    manager.update(label="changed")
    with pytest.raises(SettingsSaveError):
        manager.save()
    assert manager.settings_path.read_bytes() == original


def test_legacy_plaintext_and_age_prefix_input(encryption: SecretEncryption, mocker: MockerFixture):
    path = encryption.config.settings_path
    path.write_text(json.dumps({"secret": "legacy", "child": {"token": "nested"}, "items": ["legacy item"]}))
    manager = SettingsManager(Settings)
    manager.update(secret="age:plaintext")
    manager.save()
    data = json.loads(path.read_text())
    assert data["secret"].startswith("age:")
    assert data["items"][0].startswith("age:")
    mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    assert cast(Settings, SettingsManager(Settings).settings_instance).secret.get_secret_value() == "age:plaintext"


def test_age_in_validator_message_does_not_mark_encrypted_input_malformed(encryption: SecretEncryption):
    class AgeSettings(BaseModel):
        secret: EncryptedSecretStr
        age: int

        @field_validator("age")
        @classmethod
        def enforce_minimum_age(cls, value: int) -> int:
            if value < 18:
                raise ValueError("minimum age: 18")
            return value

    encryption.config.settings_path.write_text(json.dumps({"secret": "private", "age": 17}))
    manager = SettingsManager(AgeSettings)

    assert "minimum age: 18" in manager.invalid_warnings["age"]
    assert cast(AgeSettings, manager.settings_instance).secret.get_secret_value() == "private"


def test_explicit_encrypted_type_decrypts_while_regular_types_preserve_ciphertext(encryption: SecretEncryption):
    class MixedSettings(BaseModel):
        encrypted: EncryptedSecretStr
        ordinary: PlaintextSecretStr
        text: str

    path = encryption.config.settings_path
    ciphertext = encryption.encrypt("secret")
    path.write_text(json.dumps({"encrypted": ciphertext, "ordinary": ciphertext, "text": ciphertext}))
    manager = SettingsManager(MixedSettings)
    instance = cast(MixedSettings, manager.settings_instance)

    assert instance.encrypted.get_secret_value() == "secret"
    assert instance.ordinary.get_secret_value() == ciphertext
    assert instance.text == ciphertext

    manager.save()
    saved = json.loads(path.read_text())
    assert encryption.decrypt(saved["encrypted"]) == "secret"
    assert saved["ordinary"] == ciphertext
    assert saved["text"] == ciphertext


def test_invalid_models_never_save_secret_plaintext(encryption: SecretEncryption):
    class Invalid(BaseModel):
        required: int
        optional: EncryptedSecretStr | None = EncryptedSecretStr("plaintext default")
        tokens: list[EncryptedSecretStr] = [EncryptedSecretStr("plaintext item")]
        nested: Child = Child.model_construct(token=EncryptedSecretStr("plaintext nested"))

    manager = SettingsManager(Invalid)
    manager.save()
    data = json.loads(manager.settings_path.read_text())
    assert data["optional"].startswith("age:")
    assert data["tokens"][0].startswith("age:")
    assert data["nested"]["token"].startswith("age:")


def test_validators_decrypt_on_load_update_and_validate(encryption: SecretEncryption, mocker: MockerFixture):
    seen: list[str] = []

    class Validated(BaseModel):
        secret: EncryptedSecretStr
        label: str = "a"

        @field_validator("secret")
        @classmethod
        def inspect_secret(cls, value: EncryptedSecretStr) -> EncryptedSecretStr:
            seen.append(value.get_secret_value())
            return value

    cast(EncryptionConfig, encryption.config).encryption_cache_ttl = 60
    path = encryption.config.settings_path
    ciphertext = encryption.encrypt("private plaintext")
    path.write_text(json.dumps({"secret": ciphertext}))
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    manager = SettingsManager(Validated)
    secret = cast(Validated, manager.settings_instance).secret
    manager.update(label="changed")
    manager.validate()
    assert seen == ["private plaintext"] * 3
    assert cast(Validated, manager.settings_instance).secret is secret
    prompt.assert_called_once()
    validated_values = seen.copy()
    manager.save()
    assert seen == validated_values
    assert json.loads(path.read_text())["secret"] == ciphertext
    prompt.assert_called_once()


def test_sets_nested_collections_and_secret_fields(encryption: SecretEncryption, mocker: MockerFixture):
    class Collections(BaseModel):
        children: list[Child] = [Child.model_validate({"token": "nested"})]
        tokens: set[EncryptedSecretStr] = {EncryptedSecretStr("one"), EncryptedSecretStr("two")}
        frozen: frozenset[EncryptedSecretStr] = frozenset({EncryptedSecretStr("three")})
        renamed: EncryptedSecretStr = EncryptedSecretStr("four")
        label: str = "label"

    manager = SettingsManager(Collections)
    manager.save()
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    manager = SettingsManager(Collections)
    manager.update(label="updated")
    manager.save()
    data = json.loads(manager.settings_path.read_text())
    assert data["renamed"].startswith("age:")
    assert data["children"][0]["token"].startswith("age:")
    assert all(value.startswith("age:") for value in data["tokens"] + data["frozen"])
    prompt.assert_called()
    assert {item.get_secret_value() for item in cast(Collections, manager.settings_instance).tokens} == {"one", "two"}


def test_validation_errors_and_new_secret_input(encryption: SecretEncryption, mocker: MockerFixture):
    seen: list[str] = []

    class Validated(BaseModel):
        secret: EncryptedSecretStr
        label: str = "a"

        @field_validator("secret")
        @classmethod
        def inspect_secret(cls, value: EncryptedSecretStr) -> EncryptedSecretStr:
            plaintext = value.get_secret_value()
            seen.append(plaintext)
            if plaintext != "allowed":
                raise ValueError("secret rejected")
            return value

    path = encryption.config.settings_path
    original = json.dumps({"secret": encryption.encrypt("rejected plaintext")})
    path.write_text(original)
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    debug = mocker.patch("typerdrive.settings.manager.logger.debug")
    manager = SettingsManager(Validated)
    assert "secret rejected" in manager.invalid_warnings["secret"]
    manager.update(label="changed")
    assert "secret rejected" in manager.invalid_warnings["secret"]
    with pytest.raises(ValidationError, match="secret rejected") as error:
        manager.validate()
    assert "rejected plaintext" not in str(error.value)
    assert "rejected plaintext" not in str(manager.invalid_warnings)
    assert "rejected plaintext" not in str(debug.call_args_list)
    assert path.read_text() == original
    assert seen == ["rejected plaintext"] * 3
    prompt.assert_called()
    manager.update(secret="new invalid plaintext")
    assert seen[-1] == "new invalid plaintext"
    assert "secret rejected" in manager.invalid_warnings["secret"]
    with pytest.raises(ValidationError, match="secret rejected"):
        manager.validate()
    assert path.read_text() == original
    manager.update(secret="allowed")
    assert seen[-1] == "allowed"
    assert not manager.invalid_warnings
    manager.validate()
    manager.save()
    assert json.loads(path.read_text())["secret"].startswith("age:")


def test_encrypted_secret_does_not_retain_manager(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.config.settings_path.write_text(json.dumps({"secret": encryption.encrypt("secret")}))
    manager = SettingsManager(Settings)
    secret = cast(Settings, manager.settings_instance).secret
    manager_ref = weakref.ref(manager)
    del manager
    gc.collect()
    assert manager_ref() is None
    mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    assert secret.get_secret_value() == "secret"


def test_foreign_secret_decrypts_during_validation(encryption: SecretEncryption, mocker: MockerFixture):
    seen: list[str] = []

    class Validated(BaseModel):
        secret: EncryptedSecretStr | None = None

        @field_validator("secret")
        @classmethod
        def inspect_secret(cls, value: EncryptedSecretStr | None) -> EncryptedSecretStr | None:
            if value is not None:
                seen.append(value.get_secret_value())
            return value

    encryption.config.settings_path.write_text(json.dumps({"secret": encryption.encrypt("foreign secret")}))
    original = SettingsManager(Settings)
    secret = cast(Settings, original.settings_instance).secret
    encryption.config.settings_path.unlink()
    other = SettingsManager(Validated)
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    other.update(secret=secret)
    assert seen == ["foreign secret"]
    assert cast(Validated, other.settings_instance).secret is secret
    prompt.assert_called_once()


def test_nested_validators_decrypt(encryption: SecretEncryption, mocker: MockerFixture):
    seen: list[tuple[str, str]] = []
    nested = SettingsManager(Settings)

    class ValidatedChild(BaseModel):
        secret: EncryptedSecretStr

        @field_validator("secret")
        @classmethod
        def inspect_secret(cls, value: EncryptedSecretStr) -> EncryptedSecretStr:
            nested.construct_instance()
            seen.append(("child", value.get_secret_value()))
            return value

    class Validated(BaseModel):
        child: ValidatedChild

        @field_validator("child")
        @classmethod
        def inspect_child(cls, value: ValidatedChild) -> ValidatedChild:
            seen.append(("parent", value.secret.get_secret_value()))
            return value

    encryption.config.settings_path.write_text(json.dumps({"child": {"secret": encryption.encrypt("nested secret")}}))
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    manager = SettingsManager(Validated)
    manager.update()
    manager.validate()
    # The child validator runs once on load. Already-validated child instances are not re-validated on later
    # updates, but the parent validator still runs each time and must see the decrypted value.
    assert seen == [("child", "nested secret")] + [("parent", "nested secret")] * 3
    prompt.assert_called()


def test_validator_that_does_not_inspect_secret_stays_lazy(encryption: SecretEncryption, mocker: MockerFixture):
    class Validated(BaseModel):
        secret: EncryptedSecretStr
        label: str = "a"

        @field_validator("secret")
        @classmethod
        def retain_secret(cls, value: EncryptedSecretStr) -> EncryptedSecretStr:
            assert str(value) == "**********"
            return value

    path = encryption.config.settings_path
    ciphertext = encryption.encrypt("private plaintext")
    path.write_text(json.dumps({"secret": ciphertext}))
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    decrypt = mocker.spy(SecretEncryption, "decrypt")
    manager = SettingsManager(Validated)
    manager.update(label="changed")
    manager.validate()
    manager.save()
    assert json.loads(path.read_text())["secret"] == ciphertext
    prompt.assert_not_called()
    decrypt.assert_not_called()


def test_explicit_encrypted_type_decrypts_nested_ciphertext(encryption: SecretEncryption):
    class Nested(BaseModel):
        items: list[Child]

    path = encryption.config.settings_path
    path.write_text(json.dumps({"items": [{"token": encryption.encrypt("secret")}]}))
    manager = SettingsManager(Nested)
    secret = cast(Nested, manager.settings_instance).items[0].token

    assert isinstance(secret, EncryptedSecretStr)
    assert secret.get_secret_value() == "secret"


def test_validator_runtime_error_propagates(encryption: SecretEncryption, mocker: MockerFixture):
    fail = False

    class Validated(BaseModel):
        secret: EncryptedSecretStr

        @field_validator("secret")
        @classmethod
        def inspect_secret(cls, value: EncryptedSecretStr) -> EncryptedSecretStr:
            if fail:
                value.get_secret_value()
                raise RuntimeError("validator failed")
            return value

    path = encryption.config.settings_path
    original = json.dumps({"secret": encryption.encrypt("private plaintext")})
    path.write_text(original)
    manager = SettingsManager(Validated)
    mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    fail = True
    with pytest.raises(RuntimeError, match="validator failed"):
        manager.validate()
    assert path.read_text() == original


def test_update_never_logs_values(encryption: SecretEncryption, mocker: MockerFixture):
    debug = mocker.patch("typerdrive.settings.manager.logger.debug")
    manager = SettingsManager(Settings)
    manager.update(secret="private value", label="other value")
    assert "private value" not in str(debug.call_args_list)
    assert "other value" not in str(debug.call_args_list)


def test_untyped_values_without_secrets_still_save(encryption: SecretEncryption):
    class Untyped(BaseModel):
        value: Any = {"nested": ["ordinary"]}

    manager = SettingsManager(Untyped)
    manager.save()
    assert json.loads(manager.settings_path.read_text()) == {"value": {"nested": ["ordinary"]}}


class CustomSecret(PlaintextSecretStr):
    pass


@pytest.mark.parametrize("annotation", [CustomSecret, CustomSecret | None, CustomSecret | int, str | CustomSecret])
def test_secret_subclasses_remain_plaintext(encryption: SecretEncryption, annotation: Any):
    class SubclassSettings(BaseModel):
        value: annotation

    manager = SettingsManager(SubclassSettings)
    manager.update(value=CustomSecret("private"))
    manager.save()

    assert json.loads(manager.settings_path.read_text()) == {"value": "private"}


@pytest.mark.parametrize(
    "plaintext", ["age:ordinary", "age:", "age:YWJj", "age:" + base64.b64encode(b"age-encryption.org/v1\n").decode()]
)
def test_age_prefixed_plaintext_round_trips_for_regular_secret_types(encryption: SecretEncryption, plaintext: str):
    class Legacy(BaseModel):
        secret: PlaintextSecretStr
        optional: PlaintextSecretStr | None
        union: str | PlaintextSecretStr

    path = encryption.config.settings_path
    path.write_text(json.dumps({"secret": plaintext, "optional": plaintext, "union": plaintext}))
    manager = SettingsManager(Legacy)
    instance = cast(Legacy, manager.settings_instance)
    assert instance.secret.get_secret_value() == plaintext
    assert instance.optional is not None and instance.optional.get_secret_value() == plaintext
    assert instance.union == plaintext
    manager.save()
    assert json.loads(path.read_text()) == {"secret": plaintext, "optional": plaintext, "union": plaintext}


def test_same_recipient_nested_ciphertext_remains_lazy_and_is_preserved(
    encryption: SecretEncryption, mocker: MockerFixture
):
    class NestedSettings(BaseModel):
        child: Child = Child.model_validate({"token": "nested secret"})
        label: str = "original"

    manager = SettingsManager(NestedSettings)
    manager.save()
    ciphertext = json.loads(manager.settings_path.read_text())["child"]["token"]
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    manager = SettingsManager(NestedSettings)
    manager.update(label="changed")
    manager.save()

    assert json.loads(manager.settings_path.read_text())["child"]["token"] == ciphertext
    prompt.assert_not_called()


def test_zero_ttl_validates_all_retained_ciphertexts_with_one_prompt(
    encryption: SecretEncryption, mocker: MockerFixture
):
    class MultiSecret(BaseModel):
        first: EncryptedSecretStr
        nested: Child
        items: list[EncryptedSecretStr]
        label: str = "original"

    ciphertexts = {
        "first": encryption.encrypt("first secret"),
        "nested": {"token": encryption.encrypt("nested secret")},
        "items": [encryption.encrypt("item one"), encryption.encrypt("item two")],
    }
    path = encryption.config.settings_path
    path.write_text(json.dumps(ciphertexts))
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    manager = SettingsManager(MultiSecret)
    manager.update(label="changed")
    manager.save()

    saved = json.loads(path.read_text())
    assert saved["first"] == ciphertexts["first"]
    assert saved["nested"]["token"] == ciphertexts["nested"]["token"]
    assert saved["items"] == ciphertexts["items"]
    prompt.assert_not_called()
    assert not encryption.cache_path.exists()


def test_passwordless_settings_save_and_reload_without_prompt(tmp_path: Path, mocker: MockerFixture):
    config = EncryptionConfig(
        app_name="passwordless",
        state_home=tmp_path / "passwordless-state",
        cache_home=tmp_path / "passwordless-cache",
    )
    encryption = SecretEncryption(config)
    encryption.setup(None)
    mocker.patch("typerdrive.settings.manager.get_typerdrive_config", return_value=config)
    mocker.patch("typerdrive.settings.secrets.encryption.get_typerdrive_config", return_value=config)
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    manager = SettingsManager(Settings)
    manager.save()
    ciphertext = json.loads(config.settings_path.read_text())["secret"]
    reloaded = SettingsManager(Settings)
    reloaded.update(label="changed")
    reloaded.save()

    assert json.loads(config.settings_path.read_text())["secret"] == ciphertext
    prompt.assert_not_called()


def test_encryption_allows_nonsecret_validation_alias_overlapping_secret_input(encryption: SecretEncryption):
    class AliasedSettings(BaseModel):
        secret: EncryptedSecretStr
        label: str = Field(default="label", validation_alias="secret")

    encryption.config.settings_path.write_text(json.dumps({"secret": "private value"}))

    manager = SettingsManager(AliasedSettings)

    assert isinstance(manager.settings_instance, AliasedSettings)


def test_regular_secret_type_keeps_plaintext_alias_behavior(encryption: SecretEncryption):
    class LegacyAliasSettings(BaseModel):
        model_config = {"populate_by_name": True}

        token: PlaintextSecretStr = Field(alias="token-wire")

    path = encryption.config.settings_path
    path.write_text(json.dumps({"token-wire": "legacy plaintext"}))

    manager = SettingsManager(LegacyAliasSettings)
    assert cast(LegacyAliasSettings, manager.settings_instance).token.get_secret_value() == "legacy plaintext"
    manager.update(token="updated plaintext")
    manager.save()

    assert json.loads(path.read_text()) == {"token": "updated plaintext"}
    reloaded = SettingsManager(LegacyAliasSettings)
    assert cast(LegacyAliasSettings, reloaded.settings_instance).token.get_secret_value() == "updated plaintext"


def test_invalid_unrelated_field_preserves_encrypted_values_in_nested_collections(encryption: SecretEncryption):
    class ChildSettings(BaseModel):
        token: EncryptedSecretStr

    class PartialSettings(BaseModel):
        secret: EncryptedSecretStr
        child: ChildSettings
        tokens: list[EncryptedSecretStr]
        count: int

    ciphertexts = {
        "secret": encryption.encrypt("secret value"),
        "child": encryption.encrypt("nested value"),
        "tokens": [encryption.encrypt("first value"), encryption.encrypt("second value")],
    }
    encryption.config.settings_path.write_text(
        json.dumps(
            {
                "secret": ciphertexts["secret"],
                "child": {"token": ciphertexts["child"]},
                "tokens": ciphertexts["tokens"],
                "count": "invalid",
            }
        )
    )

    manager = SettingsManager(PartialSettings)

    assert manager.invalid_warnings
    assert isinstance(cast(PartialSettings, manager.settings_instance).secret, EncryptedSecretStr)
    assert isinstance(cast(PartialSettings, manager.settings_instance).child.token, EncryptedSecretStr)
    assert all(
        isinstance(value, EncryptedSecretStr) for value in cast(PartialSettings, manager.settings_instance).tokens
    )

    manager.save()

    saved = json.loads(manager.settings_path.read_text())
    assert saved["secret"] == ciphertexts["secret"]
    assert saved["child"]["token"] == ciphertexts["child"]
    assert saved["tokens"] == ciphertexts["tokens"]
    assert saved["count"] == "invalid"
