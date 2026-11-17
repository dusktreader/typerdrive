import base64
import json
import os
import stat
from pathlib import Path
from typing import cast

import pytest
from pytest_mock import MockerFixture
from typerdrive import EncryptedSecretStr
from typerdrive.config import TyperdriveConfig
from typerdrive.settings.exceptions import SecretEncryptionError
from typerdrive.settings.secrets.encryption import SecretEncryption

pytest.importorskip("pyrage")


class EncryptionConfig(TyperdriveConfig):
    encryption_cache_ttl: int = 60


@pytest.fixture
def encryption(tmp_path: Path) -> SecretEncryption:
    return SecretEncryption(
        EncryptionConfig(app_name="test", state_home=tmp_path / "state", cache_home=tmp_path / "cache")
    )


def test_wildcard_import_includes_encrypted_secret_str():
    namespace = {}
    exec("from typerdrive import *", namespace)
    assert namespace["EncryptedSecretStr"] is EncryptedSecretStr


def test_round_trip_and_cache_reuse(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.setup("passphrase")
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    ciphertext = encryption.encrypt("secret ☄")
    assert ciphertext.startswith("age:")
    assert b"secret" not in base64.b64decode(ciphertext[4:])
    assert encryption.decrypt(ciphertext) == "secret ☄"
    assert encryption.decrypt(ciphertext) == "secret ☄"
    prompt.assert_called_once_with("Secret encryption passphrase", hide_input=True)
    assert SecretEncryption(encryption.config).decrypt(ciphertext) == "secret ☄"
    prompt.assert_called_once()


def test_unlock_wrong_passphrase_and_lock(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.setup("right")
    ciphertext = encryption.encrypt("secret")
    with pytest.raises(SecretEncryptionError, match="passphrase"):
        encryption.unlock("wrong")
    assert not encryption.cache_path.exists()
    encryption.unlock("right")
    with pytest.raises(SecretEncryptionError, match="passphrase"):
        encryption.unlock("wrong")
    encryption.lock()
    assert not encryption.cache_path.exists()
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="right")
    assert encryption.decrypt(ciphertext) == "secret"
    prompt.assert_called_once()


def test_rotation_preserves_secrets_and_invalidates_cache(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.setup("old")
    ciphertext = encryption.encrypt("secret")
    encryption.unlock("old")
    old_cache = encryption.cache_path.read_bytes()
    with pytest.raises(SecretEncryptionError, match="passphrase"):
        encryption.change_passphrase("wrong", "new")
    assert encryption.decrypt(ciphertext) == "secret"
    encryption.change_passphrase("old", "new")
    assert not encryption.cache_path.exists()
    encryption.cache_path.write_bytes(old_cache)
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="new")
    assert encryption.decrypt(ciphertext) == "secret"
    prompt.assert_called_once()
    with pytest.raises(SecretEncryptionError, match="passphrase"):
        encryption.unlock("old")
    encryption.unlock("new")


def test_expiry_unlinks_before_prompt(encryption: SecretEncryption, mocker: MockerFixture):
    mock_time = mocker.patch("typerdrive.settings.secrets.encryption.time.time", return_value=1000)
    encryption.setup("passphrase")
    ciphertext = encryption.encrypt("secret")
    encryption.unlock("passphrase")
    mock_time.return_value = 1060

    def prompt(*args, **kwargs):
        assert not encryption.cache_path.exists()
        return "passphrase"

    mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", side_effect=prompt)
    assert encryption.decrypt(ciphertext) == "secret"


def test_zero_ttl_disables_cache(encryption: SecretEncryption, mocker: MockerFixture):
    cast(EncryptionConfig, encryption.config).encryption_cache_ttl = 0
    encryption.setup("passphrase")
    encryption.unlock("passphrase")
    assert not encryption.cache_path.exists()
    ciphertext = encryption.encrypt("secret")
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    assert encryption.decrypt(ciphertext) == "secret"
    assert encryption.decrypt(ciphertext) == "secret"
    assert prompt.call_count == 2
    assert not encryption.cache_path.exists()


def test_permissions(encryption: SecretEncryption):
    encryption.setup("passphrase")
    encryption.unlock("passphrase")
    assert stat.S_IMODE(encryption.material_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(encryption.cache_path.stat().st_mode) == 0o600
    encryption.change_passphrase("passphrase", "new")
    assert stat.S_IMODE(encryption.material_path.stat().st_mode) == 0o600


def test_no_overwrite_existing_keys(encryption: SecretEncryption):
    encryption.setup("passphrase")
    original = encryption.material_path.read_bytes()
    with pytest.raises(SecretEncryptionError, match="already exists"):
        encryption.setup("another")
    assert encryption.material_path.read_bytes() == original
    encryption.unlock("passphrase")


def test_no_overwrite_even_if_material_is_malformed(encryption: SecretEncryption):
    encryption.material_path.parent.mkdir(parents=True)
    encryption.material_path.write_text("invalid")
    with pytest.raises(SecretEncryptionError, match="already exists"):
        encryption.setup("passphrase")
    assert encryption.material_path.read_text() == "invalid"
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.encrypt("secret")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.unlock("passphrase")


def test_missing_material_never_generates_keys(encryption: SecretEncryption, mocker: MockerFixture):
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.encrypt("secret")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.unlock("passphrase")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.change_passphrase("old", "new")
    prompt.assert_not_called()
    assert not encryption.material_path.exists()


def test_tampering(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.setup("passphrase")
    ciphertext = encryption.encrypt("secret")
    encryption.unlock("passphrase")
    data = bytearray(base64.b64decode(ciphertext[4:]))
    data[-1] ^= 1
    with pytest.raises(SecretEncryptionError, match="decrypt"):
        encryption.decrypt("age:" + base64.b64encode(data).decode())
    with pytest.raises(SecretEncryptionError, match="ciphertext"):
        encryption.decrypt("age:not base64!")
    material = json.loads(encryption.material_path.read_text())
    wrapped = bytearray(base64.b64decode(material["identity"]))
    wrapped[-1] ^= 1
    material["identity"] = base64.b64encode(wrapped).decode()
    encryption.material_path.write_text(json.dumps(material))
    with pytest.raises(SecretEncryptionError, match="passphrase"):
        encryption.unlock("passphrase")
    material["identity"] = "broken"
    encryption.material_path.write_text(json.dumps(material))
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.decrypt(ciphertext)
    prompt.assert_not_called()


def test_tampered_cache_is_discarded(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.setup("passphrase")
    ciphertext = encryption.encrypt("secret")
    encryption.unlock("passphrase")
    encryption.cache_path.write_text("not json")
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="passphrase")
    assert encryption.decrypt(ciphertext) == "secret"
    prompt.assert_called_once()


def test_missing_optional_dependency_is_reported_for_encrypted_secret_import(run_without_pyrage):
    run_without_pyrage(
        """
try:
    from typerdrive import EncryptedSecretStr
except ImportError as error:
    assert "typerdrive[encrypt-secrets]" in str(error)
else:
    raise AssertionError("EncryptedSecretStr imported without pyrage")
"""
    )


@pytest.mark.parametrize("ttl", [0, 60])
def test_passwordless_round_trip(encryption: SecretEncryption, mocker: MockerFixture, ttl: int):
    cast(EncryptionConfig, encryption.config).encryption_cache_ttl = ttl
    encryption.setup(None)
    material = json.loads(encryption.material_path.read_text())
    assert material["mode"] == "passwordless"
    assert material["identity"].startswith("AGE-SECRET-KEY-")
    assert stat.S_IMODE(encryption.material_path.stat().st_mode) == 0o600
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    ciphertext = encryption.encrypt("secret ☄")
    assert ciphertext.startswith("age:")
    assert b"secret" not in base64.b64decode(ciphertext[4:])
    assert encryption.decrypt(ciphertext) == "secret ☄"
    assert SecretEncryption(encryption.config).decrypt(ciphertext) == "secret ☄"
    assert not encryption.cache_path.exists()
    prompt.assert_not_called()


def test_passwordless_password_operations_and_lock(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.setup(None)
    original = encryption.material_path.read_bytes()
    encryption.cache_path.parent.mkdir(parents=True)
    encryption.cache_path.write_text("stale")
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    with pytest.raises(SecretEncryptionError, match="unlock passwordless"):
        encryption.unlock("anything")
    with pytest.raises(SecretEncryptionError, match="passwordless.*migration"):
        encryption.change_passphrase("old", "new")
    assert encryption.material_path.read_bytes() == original
    assert encryption.decrypt(encryption.encrypt("secret")) == "secret"
    assert encryption.cache_path.read_text() == "stale"
    encryption.lock()
    assert not encryption.cache_path.exists()
    assert encryption.decrypt(encryption.encrypt("secret")) == "secret"
    assert not encryption.cache_path.exists()
    prompt.assert_not_called()


@pytest.mark.parametrize("first,second", [(None, None), (None, "password"), ("password", None)])
def test_duplicate_setup_modes(encryption: SecretEncryption, first: str | None, second: str | None):
    encryption.setup(first)
    original = encryption.material_path.read_bytes()
    with pytest.raises(SecretEncryptionError, match="already exists"):
        encryption.setup(second)
    assert encryption.material_path.read_bytes() == original


def test_empty_passphrase_rejected(encryption: SecretEncryption):
    with pytest.raises(SecretEncryptionError, match="empty"):
        encryption.setup("")
    assert not encryption.material_path.exists()
    encryption.setup("old")
    original = encryption.material_path.read_bytes()
    with pytest.raises(SecretEncryptionError, match="empty"):
        encryption.change_passphrase("old", "")
    assert encryption.material_path.read_bytes() == original
    encryption.unlock("old")


@pytest.mark.parametrize("tamper", ["identity", "recipient", "mismatch", "mode", "extra", "missing"])
def test_passwordless_material_tampering(encryption: SecretEncryption, mocker: MockerFixture, tamper: str):
    age = pytest.importorskip("pyrage")
    encryption.setup(None)
    ciphertext = encryption.encrypt("secret")
    material = json.loads(encryption.material_path.read_text())
    if tamper == "identity":
        material["identity"] = "invalid"
    elif tamper == "recipient":
        material["recipient"] = "invalid"
    elif tamper == "mismatch":
        material["recipient"] = str(age.x25519.Identity.generate().to_public())
    elif tamper == "mode":
        material["mode"] = "unknown"
    elif tamper == "extra":
        material["extra"] = True
    elif tamper == "missing":
        del material["mode"]
    encryption.material_path.write_text(json.dumps(material))
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.encrypt("secret")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.decrypt(ciphertext)
    prompt.assert_not_called()
    assert not encryption.cache_path.exists()


def test_protected_material_and_ciphertext(encryption: SecretEncryption, mocker: MockerFixture):
    age = pytest.importorskip("pyrage")
    identity = age.x25519.Identity.generate()
    wrapped = age.passphrase.encrypt(str(identity).encode(), "legacy")
    material = {
        "recipient": str(identity.to_public()),
        "identity": base64.b64encode(wrapped).decode(),
        "mode": "passphrase",
    }
    encryption.material_path.parent.mkdir(parents=True)
    encryption.material_path.write_text(json.dumps(material))
    encryption.material_path.chmod(0o600)
    data = age.encrypt(b"legacy secret", [identity.to_public()])
    ciphertext = "age:" + base64.b64encode(data).decode()
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="legacy")
    assert encryption.decrypt(ciphertext) == "legacy secret"
    prompt.assert_called_once()
    encryption.change_passphrase("legacy", "new")
    with pytest.raises(SecretEncryptionError, match="passphrase"):
        encryption.unlock("legacy")
    encryption.unlock("new")
    assert encryption.decrypt(ciphertext) == "legacy secret"


def test_restrictive_umask_still_creates_usable_private_material(encryption: SecretEncryption):
    encryption.material_path.parent.mkdir(parents=True)
    old_mask = os.umask(0o777)
    try:
        encryption.setup(None)
    finally:
        os.umask(old_mask)
    assert stat.S_IMODE(encryption.material_path.stat().st_mode) == 0o600
    assert encryption.decrypt(encryption.encrypt("secret")) == "secret"


def test_protected_recipient_mismatch_fails(encryption: SecretEncryption, mocker: MockerFixture):
    age = pytest.importorskip("pyrage")
    encryption.setup("password")
    material = json.loads(encryption.material_path.read_text())
    material["recipient"] = str(age.x25519.Identity.generate().to_public())
    encryption.material_path.write_text(json.dumps(material))
    ciphertext = encryption.encrypt("secret")
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt", return_value="password")
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.decrypt(ciphertext)
    with pytest.raises(SecretEncryptionError, match="material"):
        encryption.unlock("password")
    prompt.assert_called_once()
    assert not encryption.cache_path.exists()


@pytest.mark.parametrize("passphrase", [None, "password"])
def test_is_passphrase_protected(encryption: SecretEncryption, mocker: MockerFixture, passphrase: str | None):
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    with pytest.raises(SecretEncryptionError, match="material"):
        _ = encryption.is_passphrase_protected
    encryption.setup(passphrase)
    assert encryption.is_passphrase_protected is (passphrase is not None)
    prompt.assert_not_called()


def test_protected_material_with_grease_stanzas(encryption: SecretEncryption, mocker: MockerFixture):
    encryption.setup("password")
    material = json.loads(encryption.material_path.read_text())
    wrapped = base64.b64decode(material["identity"])
    prefix = b"age-encryption.org/v1\n"
    grease = b"-> test-grease argument\n" + b"A" * 64 + b"\n\n"
    wrapped = wrapped.replace(prefix, prefix + grease, 1).replace(b"--- ", b"-> another-grease\n\n--- ", 1)
    material["identity"] = base64.b64encode(wrapped).decode()
    encryption.material_path.write_text(json.dumps(material))
    prompt = mocker.patch("typerdrive.settings.secrets.encryption.typer.prompt")
    decrypt = mocker.patch("pyrage.passphrase.decrypt")
    assert encryption.is_passphrase_protected
    assert encryption.encrypt("secret").startswith("age:")
    prompt.assert_not_called()
    decrypt.assert_not_called()
