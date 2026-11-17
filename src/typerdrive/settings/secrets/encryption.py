"""
Encrypt settings secrets using [age](https://age-encryption.org) with an X25519 key pair.

Secrets are encrypted for a public recipient, and decrypted with the matching private identity. The recipient and
identity are persisted as "material", where the identity is either protected by a passphrase or stored as-is. See the
settings feature documentation for a full explanation.
"""

import base64
import binascii
import hashlib
import json
import math
import time
from dataclasses import dataclass

import typer
from pydantic import BaseModel, ConfigDict

from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.file_ops import atomic_write
from typerdrive.settings.constants import EncryptionMode
from typerdrive.settings.exceptions import SecretEncryptionError

try:
    import pyrage
except ModuleNotFoundError as exc:
    if exc.name != "pyrage":
        raise
    raise ImportError(
        "EncryptedSecretStr requires the 'encrypt-secrets' extra: install typerdrive[encrypt-secrets]"
    ) from exc


class EncryptionMaterial(BaseModel):
    """
    The encryption material persisted on disk.

    The identity is a base64 passphrase-wrapped age identity when `mode` is `PASSPHRASE`, or the plain age identity when
    `mode` is `PASSWORDLESS`.
    """

    model_config = ConfigDict(extra="forbid")

    recipient: str
    identity: str
    mode: EncryptionMode


@dataclass(frozen=True)
class PassphraseMaterial:
    """
    Validated encryption material whose private identity is protected by a passphrase.
    """

    raw: bytes
    recipient: pyrage.x25519.Recipient
    wrapped: bytes
    """ The age identity, encrypted with the passphrase """


@dataclass(frozen=True)
class PasswordlessMaterial:
    """
    Validated encryption material whose private identity is stored without passphrase protection.
    """

    raw: bytes
    recipient: pyrage.x25519.Recipient
    identity: pyrage.x25519.Identity


LoadedMaterial = PassphraseMaterial | PasswordlessMaterial
""" The validated encryption material read from disk """


class SecretEncryption:
    """
    Manage an age recipient and its protected or passwordless identity.

    Unlocking may cache the plaintext identity in a private file until its TTL expires.
    Expiration is enforced on access, not in the background; deletion cannot guarantee
    secure erasure from storage, snapshots, backups, or memory. An interrupted atomic write
    may leave a private temporary file. Use a zero TTL to disable caching.
    """

    def __init__(self, config: TyperdriveConfig):
        self.config = config
        self.material_path = config.app_state_home / "secret-encryption.json"
        self.cache_path = config.app_cache_home / "secret-encryption-identity.json"

    @property
    def is_passphrase_protected(self) -> bool:
        """Return whether the configured identity is passphrase-protected."""
        return isinstance(self.load_material(), PassphraseMaterial)

    @property
    def recipient(self) -> str:
        """Return the configured public recipient."""
        return str(self.load_material().recipient)

    def load_material(self) -> LoadedMaterial:
        with SecretEncryptionError.handle_errors(
            "Missing, malformed, or insecure secret encryption material",
            handle_exc_class=(
                SecretEncryptionError,
                OSError,
                ValueError,
                binascii.Error,
                pyrage.RecipientError,
                pyrage.IdentityError,
            ),
        ):
            raw = self.material_path.read_bytes()
            material = EncryptionMaterial.model_validate_json(raw)
            recipient = pyrage.x25519.Recipient.from_str(material.recipient)
            if material.mode == EncryptionMode.PASSPHRASE:
                return PassphraseMaterial(
                    raw=raw,
                    recipient=recipient,
                    wrapped=base64.b64decode(material.identity, validate=True),
                )
            identity = pyrage.x25519.Identity.from_str(material.identity)
            SecretEncryptionError.require_condition(
                str(identity.to_public()) == str(recipient),
                "Secret encryption identity does not match recipient",
            )
            return PasswordlessMaterial(raw=raw, recipient=recipient, identity=identity)

    def unwrap_identity(
        self, wrapped: bytes, recipient: pyrage.x25519.Recipient, passphrase: str
    ) -> pyrage.x25519.Identity:
        try:
            value = pyrage.passphrase.decrypt(wrapped, passphrase).decode("utf-8")
            identity = pyrage.x25519.Identity.from_str(value)
            SecretEncryptionError.require_condition(
                str(identity.to_public()) == str(recipient),
                "Secret encryption identity does not match recipient",
            )
            return identity
        except (SecretEncryptionError, ValueError, UnicodeError, pyrage.DecryptError, pyrage.IdentityError) as exc:
            raise SecretEncryptionError("Invalid passphrase or secret encryption material") from exc

    def write_cache(self, identity: pyrage.x25519.Identity, raw: bytes) -> None:
        ttl = self.config.encryption_cache_ttl
        if ttl <= 0:
            self.clear_cache()
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        content = {
            "expires": time.time() + ttl,
            "material": hashlib.sha256(raw).hexdigest(),
            "identity": str(identity),
        }
        atomic_write(self.cache_path, json.dumps(content).encode("utf-8"))

    def read_cached_identity(self, raw: bytes, recipient: pyrage.x25519.Recipient) -> pyrage.x25519.Identity | None:
        if self.config.encryption_cache_ttl <= 0:
            self.clear_cache()
            return None
        if not self.cache_path.exists():
            return None
        try:
            cached = json.loads(self.cache_path.read_text())
            if (
                not isinstance(cached, dict)
                or not isinstance(cached.get("expires"), (int, float))
                or not math.isfinite(cached["expires"])
                or not time.time() < cached["expires"]
                or cached.get("material") != hashlib.sha256(raw).hexdigest()
            ):
                raise ValueError("Expired or invalid cache")
            identity = pyrage.x25519.Identity.from_str(cached["identity"])
            if str(identity.to_public()) != str(recipient):
                raise ValueError("Cached identity does not match recipient")
            return identity
        except (OSError, ValueError, TypeError, KeyError, pyrage.IdentityError):
            self.clear_cache()
            return None

    def setup(self, passphrase: str | None) -> None:
        """Create new encryption material without replacing existing material."""
        SecretEncryptionError.require_condition(
            passphrase is None or bool(passphrase),
            "Passphrase must not be empty",
        )
        identity = pyrage.x25519.Identity.generate()
        recipient = str(identity.to_public())
        if passphrase is None:
            material = EncryptionMaterial(recipient=recipient, identity=str(identity), mode=EncryptionMode.PASSWORDLESS)
        else:
            wrapped = pyrage.passphrase.encrypt(str(identity).encode("utf-8"), passphrase)
            material = EncryptionMaterial(
                recipient=recipient,
                identity=base64.b64encode(wrapped).decode("ascii"),
                mode=EncryptionMode.PASSPHRASE,
            )
        SecretEncryptionError.require_condition(
            not self.material_path.exists(follow_symlinks=False),
            "Secret encryption material already exists",
        )
        self.clear_cache()
        self.material_path.parent.mkdir(parents=True, exist_ok=True)
        with SecretEncryptionError.handle_errors(
            "Secret encryption material already exists",
            handle_exc_class=FileExistsError,
        ):
            atomic_write(self.material_path, material.model_dump_json().encode("utf-8"), create_only=True)

    def change_passphrase(self, old: str, new: str) -> None:
        """Rewrap the existing identity under a new passphrase."""
        loaded = self.load_material()
        recipient = loaded.recipient
        if not isinstance(loaded, PassphraseMaterial):
            raise SecretEncryptionError(
                "Cannot change passphrase for passwordless material; migration is not supported"
            )
        if not new:
            raise SecretEncryptionError("Passphrase must not be empty")
        identity = self.unwrap_identity(loaded.wrapped, recipient, old)
        new_wrapped = pyrage.passphrase.encrypt(str(identity).encode("utf-8"), new)
        material = EncryptionMaterial(
            recipient=str(recipient),
            identity=base64.b64encode(new_wrapped).decode("ascii"),
            mode=EncryptionMode.PASSPHRASE,
        )
        self.clear_cache()
        atomic_write(self.material_path, material.model_dump_json().encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        """Encrypt text for the configured recipient without prompting."""
        return self.encrypt_for_recipient(plaintext, self.load_material().recipient)

    @staticmethod
    def encrypt_for_recipient(plaintext: str, recipient: pyrage.x25519.Recipient) -> str:
        ciphertext = pyrage.encrypt(plaintext.encode("utf-8"), [recipient])
        return "age:" + base64.b64encode(ciphertext).decode("ascii")

    def decode_ciphertext(self, ciphertext: str) -> bytes:
        try:
            if not ciphertext.startswith("age:"):
                raise ValueError("Missing age marker")
            data = base64.b64decode(ciphertext[4:], validate=True)
            if not data.startswith(b"age-encryption.org/v1\n"):
                raise ValueError("Invalid age ciphertext")
        except (ValueError, binascii.Error) as exc:
            raise SecretEncryptionError("Malformed secret ciphertext") from exc
        return data

    def identity_for_save(self) -> pyrage.x25519.Identity:
        """Return the verified identity, prompting when protected material is not cached."""
        loaded = self.load_material()
        if isinstance(loaded, PasswordlessMaterial):
            return loaded.identity
        identity = self.read_cached_identity(loaded.raw, loaded.recipient)
        if identity is None:
            passphrase = typer.prompt("Secret encryption passphrase", hide_input=True)
            identity = self.unwrap_identity(loaded.wrapped, loaded.recipient, passphrase)
            self.write_cache(identity, loaded.raw)
        return identity

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an age-marked value, prompting only when a protected identity is not cached."""
        return self.decrypt_for_identity(ciphertext, self.identity_for_save())

    def decrypt_for_identity(self, ciphertext: str, identity: pyrage.x25519.Identity) -> str:
        """Decrypt an age-marked value with an already unlocked identity."""
        data = self.decode_ciphertext(ciphertext)
        try:
            return pyrage.decrypt(data, [identity]).decode("utf-8")
        except (pyrage.DecryptError, UnicodeError) as exc:
            raise SecretEncryptionError("Unable to decrypt secret ciphertext") from exc

    def unlock(self, passphrase: str) -> None:
        """Verify the passphrase and cache the identity when the TTL permits."""
        loaded = self.load_material()
        if not isinstance(loaded, PassphraseMaterial):
            raise SecretEncryptionError("Cannot unlock passwordless secret encryption material")
        identity = self.unwrap_identity(loaded.wrapped, loaded.recipient, passphrase)
        self.write_cache(identity, loaded.raw)

    def lock(self) -> None:
        """Remove the cached identity, if present."""
        self.clear_cache()

    def clear_cache(self) -> None:
        self.cache_path.unlink(missing_ok=True)

    def reset(self) -> None:
        """Remove the identity and any cached copy of it. Encrypted values can no longer be decrypted afterward."""
        self.clear_cache()
        self.material_path.unlink(missing_ok=True)


def get_secret_encryption() -> SecretEncryption:
    """Return a `SecretEncryption` for the current typerdrive config."""
    return SecretEncryption(get_typerdrive_config())
