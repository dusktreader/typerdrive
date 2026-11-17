"""
Provide the secret string types for settings models.

`PlaintextSecretStr` is persisted as plaintext, and `EncryptedSecretStr` is persisted as age ciphertext. Both mask
themselves in `str()` and `repr()`. Pydantic's own `SecretStr` is not supported in settings models because it
serializes to a mask.
"""

from typing import Any, Self

from pydantic import SecretStr
from pydantic_core import core_schema

from typerdrive.settings.constants import DUMP_CONTEXT_KEY, LOADING_CONTEXT_KEY, DumpMode
from typerdrive.settings.exceptions import SecretValueError


class PlaintextSecretStr(SecretStr):
    """
    A `SecretStr` that is masked for display, but is written as plaintext when serialized to JSON.

    Pydantic's `SecretStr` serializes to a mask (`**********`) in JSON mode, which would corrupt a settings file if it
    were persisted. This type behaves exactly like `SecretStr` (including masking in `str()` and `repr()`), except
    that its JSON serialization is the real value. This allows settings to be persisted with the normal pydantic
    serializers instead of walking the model by hand.

    Use this type (or `EncryptedSecretStr`) for secrets in a settings model, instead of `SecretStr`.

    Note:
        Because the plaintext is written to the settings file, protect that file with appropriate filesystem
        permissions or use `EncryptedSecretStr`.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: Any) -> core_schema.CoreSchema:
        return core_schema.with_info_plain_validator_function(
            cls.validate_value,
            json_schema_input_schema=core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialize_value,
                info_arg=True,
                when_used="always",
            ),
        )

    @classmethod
    def validate_value(cls, value: Any, info: core_schema.ValidationInfo) -> Self:
        """Wrap a `str` or any `SecretStr` as this type."""
        if isinstance(value, cls):
            return value
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not isinstance(value, str):
            raise ValueError(f"{cls.__name__} requires a string or SecretStr")
        return cls(value)

    @classmethod
    def serialize_value(cls, value: Any, info: core_schema.SerializationInfo) -> Any:
        """Return the value itself in python mode, and the plaintext in JSON mode."""
        if info.mode != "json" or not isinstance(value, SecretStr):
            return value
        return value.get_secret_value()


class EncryptedSecretStr(SecretStr):
    """
    A secret string that is plaintext in memory and age-encrypted on disk.

    The value is encrypted only when settings are saved, and decrypted only when settings are loaded from disk. Like
    `SecretStr`, it masks its value in `str()` and `repr()`.
    """

    typerdrive_encrypted = True
    """Marks this type as encrypted for settings utilities that must not import this optional module."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: Any) -> core_schema.CoreSchema:
        return core_schema.with_info_plain_validator_function(
            cls.validate_value,
            json_schema_input_schema=core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialize_value,
                info_arg=True,
                when_used="always",
            ),
        )

    @classmethod
    def validate_value(cls, value: Any, info: core_schema.ValidationInfo) -> Self:
        """Wrap a string as a secret, decrypting it first when it is being loaded from disk."""
        if isinstance(value, cls):
            return value
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        value = SecretValueError.ensure_type(value, str, "EncryptedSecretStr requires a string or SecretStr")
        context = info.context if isinstance(info.context, dict) else {}
        if context.get(LOADING_CONTEXT_KEY) and value.startswith("age:"):
            return cls.from_ciphertext(value)
        return cls(value)

    @classmethod
    def from_ciphertext(cls, ciphertext: str) -> Self:
        """Hold ciphertext without decrypting it. It is decrypted on first access to the value."""
        secret = cls("")
        secret._ciphertext = ciphertext
        return secret

    _ciphertext: str | None = None
    _decrypted: bool = False

    def _display(self) -> str:
        return "**********" if self._ciphertext is not None else super()._display()

    def get_secret_value(self) -> str:
        if self._ciphertext is not None and not self._decrypted:
            self._secret_value = _get_secret_encryption().decrypt(self._ciphertext)
            self._decrypted = True
        return super().get_secret_value()

    @classmethod
    def serialize_value(cls, value: Any, info: core_schema.SerializationInfo) -> str:
        """Serialize as ciphertext or plaintext when the dump context asks for it. Otherwise, mask the value."""
        context = info.context if isinstance(info.context, dict) else {}
        mode = context.get(DUMP_CONTEXT_KEY)
        if not isinstance(value, SecretStr):
            return value
        if info.mode != "json" and mode is None:
            return value
        if mode == DumpMode.PERSIST:
            return value.encrypt()
        if mode == DumpMode.PLAINTEXT:
            return value.get_secret_value()
        return "**********"

    def encrypt(self) -> str:
        """Return the age ciphertext of this secret for the configured recipient."""
        if self._ciphertext is not None:
            return self._ciphertext
        return _get_secret_encryption().encrypt(self.get_secret_value())


def _get_secret_encryption() -> Any:
    from typerdrive.settings.secrets.encryption import get_secret_encryption

    return get_secret_encryption()
