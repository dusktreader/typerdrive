"""
Provide constants specific to the settings feature of `typerdrive`.
"""

from enumatic import Enumatic, LowerCaseMixin, auto

LOADING_CONTEXT_KEY = "typerdrive_settings_loading"
""" The validation context key that marks settings as being loaded from disk """

DUMP_CONTEXT_KEY = "typerdrive_settings_dump"
""" The serialization context key that selects how `EncryptedSecretStr` values are dumped """


class DumpMode(Enumatic, LowerCaseMixin):
    """
    Defines how `EncryptedSecretStr` values are serialized.
    """

    PERSIST = auto()
    """ Serialize as age ciphertext """
    PLAINTEXT = auto()
    """ Serialize as the plaintext value """


class EncryptionMode(Enumatic, LowerCaseMixin):
    """
    Defines how the age identity is stored.
    """

    PASSPHRASE = auto()
    PASSWORDLESS = auto()
