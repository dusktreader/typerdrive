# Commands to manage application settings

Typical applications built with `Typer` are essentially stateless. That is, to control their behavior, you need to
provide all of the _configuration_ for the app through the use of positional arguments, options, and environment
variables.

For a complex application with many commands, this can be frustrating and slow. You find yourself passing the same
parameters over and over.

Thus, `typerdrive` provides a `settings` subcommand to help with this.


## Overview

The `typerdrive` package provides functionality to store, reuse, and update application settings through a set of
subcommands. These subcommands are bound to your app under the `settings` subcommand. These subcommands manipulate the
your app's settings and allow your other commands to access the settings values via the `@attach_settings` decorator.

Let's take a look at how we can use this powerful feature set.


## Usage

Let's start by looking at a code example:

```python {linenums="1"}
--8<-- "examples/settings/commands.py"
```

In this example, the app provides a [Pydantic](https://docs.pydantic.dev/latest/) model that describes all of the
settings values that the app needs. Then, the app calls the `add_settings_subcommand()` to add the `settings` feature to
the CLI. That's all you need to utilize the `settings` feature in your app. Now, you can access and manage your settings
through the various `settings` subcommands.

In the `report` command, you can see how the settings values may be accessed within one of the app's other commands. The
`@attach_settings` decorator adds the settings object to the app's `typer.Context`. Then, the settings can be accessed
by providing a parameter to the command that matches the `SettingsModel` type. The argument that will get the settings
object can be named anything you like!

!!! warning "Settings model type agreement"

    The type of the pydantic model passed to `@attach_settings()` **MUST** match the type used for the settings
    parameter of the command function. If the types do not match, a `Typer` exception will be raised saying that Typer
    doesn't know how to handle the argument.

Great, now let's try a few commands in this app to see how the settings commands work.

First, we will just show the config

```text
$ python examples/settings/commands.py settings show

╭─ Current settings ───────────────────────────────────────────────────────────╮
│                                                                              │
│ Settings Values                                                              │
│                                                                              │
│         name  str   ->  <UNSET>                                              │
│       planet  str   ->  <UNSET>                                              │
│  is-humanoid  bool  ->  True                                                 │
│    alignment  str   ->  neutral                                              │
│                                                                              │
│                                                                              │
│ Invalid Values                                                               │
│                                                                              │
│    name  ->  Field required                                                  │
│  planet  ->  Field required                                                  │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

As you can see, our settings initially just matches the defaults provided in the settings model. The fields that still
need to be defined are clearly identified and the settings are shown to be invalid.

Next, let's make the settings valid by setting the missing values with `bind`:

```text
$ python examples/settings/commands.py settings bind --name=jawa --planet=tatooine

╭─ Current settings ───────────────────────────────────────────────────────────╮
│                                                                              │
│ Settings Values                                                              │
│                                                                              │
│         name  str   ->  jawa                                                 │
│       planet  str   ->  tatooine                                             │
│  is-humanoid  bool  ->  True                                                 │
│    alignment  str   ->  neutral                                              │
│                                                                              │
╰─ saved to /home/dusktreader/.local/share/settings-commands-example/settin...─╯
```

Now, the settings are valid. You can also see that the settings were saved to disk for your app to use in future
commands.

Let's make an adjustment to the settings using the `update` command:

```text
$ python examples/settings/commands.py settings update --name=hutt --no-is-humanoid

╭─ Current settings ───────────────────────────────────────────────────────────╮
│                                                                              │
│ Settings Values                                                              │
│                                                                              │
│         name  str   ->  hutt                                                 │
│       planet  str   ->  tatooine                                             │
│  is-humanoid  bool  ->  False                                                │
│    alignment  str   ->  neutral                                              │
│                                                                              │
╰─ saved to /home/dusktreader/.local/share/settings-commands-example/settin...─╯
```

Notice that the `update` command only changed the values specified and left the others alone.

Now that we're happy with our settings, lets run our `report` command to try out using these app settings:

```text
$ python examples/settings/commands.py report
Look at this neutral hutt from tatooine slithering by.
```

Great! Our app is able to use the settings in any command!

Finally, let's clear out the settings with `reset`:

```text
$ python examples/settings/commands.py settings reset
Are you sure you want to reset your settings? [y/N]: y

╭─ Current settings ───────────────────────────────────────────────────────────╮
│                                                                              │
│ Settings Values                                                              │
│                                                                              │
│         name  str   ->  <UNSET>                                              │
│       planet  str   ->  <UNSET>                                              │
│  is-humanoid  bool  ->  True                                                 │
│    alignment  str   ->  neutral                                              │
│                                                                              │
│                                                                              │
│ Invalid Values                                                               │
│                                                                              │
│    name  ->  Field required                                                  │
│  planet  ->  Field required                                                  │
│                                                                              │
╰─ saved to /home/dusktreader/.local/share/settings-commands-example/settin...─╯
```

Now, all the settings are returned to their initial values. Those that have no default values are now invalid.


## Details

Let's take a closer look at details of each `settings` subcommand.


### `bind`

The `bind` command is used to set all your app settings at once. It is very similar to the `update` command with a few
key differences. First, the `bind` command will not allow you to have an invalid configuration when it is done. It will
require each settings value without a default to be explicitly set. After you have provided the values through command
options, the final configuration will be validated before it is saved.

Like the other `settings` subcommands that modify the settings, `bind` will write a settings file to disk when it is
finished. The settings file is stored in `~/.local/share/<your-app-name>/settings.json`. If the parent directories for
this file don't exist, they will be created.

!!! note "Not supported on Windows"

    Currently, the `typerdrive` `settings` commands are only configured to work on Linux and MacOS. I have plans to add
    support for Windows as well eventually, but at the moment `typerdrive` is dependent on settings being stored below
    `~/.local/share`

Each settings value from the settings model you provide is mapped to a CLI option for the `bind` subcommand. If the
value has a default in the model, then the option will use the same default. Boolean values use the normal convention
from Typer with `--flag` or `--no-flag` controlling the value of the boolean.

The help text from our example above for the `bind` subcommand looks like this:

```text
$ python examples/settings/commands.py settings bind --help

 Usage: commands.py settings bind [OPTIONS]

╭─ Options ──────────────────────────────────────────────────────────────────────────────────╮
│ *  --name                               TEXT  [default: None] [required]                   │
│ *  --planet                             TEXT  [default: None] [required]                   │
│    --is-humanoid    --no-is-humanoid          [default: is-humanoid]                       │
│    --alignment                          TEXT  [default: neutral]                           │
│    --help                                     Show this message and exit.                  │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
```


### `update`

The `update` command is used to update a subset of the available settings values. It works very similarly to the `bind`
command, however, the `update` command will allow your configuration to be invalid when it is finished. This might be
useful if you want to establish some values in your settings now but need to look something up before you are finished
configuring the app.

Like the other subcommands that modify settings, `update` will save all changes to disk.

Each settings value from the settings model is mapped to an _optional_ CLI option for the `update` subcommand. If the
settings value is a boolean, it will use the `--flag` / `--no-flag` format. All other commands will default to `None` if
they are not passed and the `update` command will ignore them.

The help text from our example above for the `update` subcommand looks like this:

```text
$ python examples/settings/commands.py settings update --help

 Usage: commands.py settings update [OPTIONS]

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --name                               TEXT  [default: None]                                                                                                                                                                                                                              │
│ --planet                             TEXT  [default: None]                                                                                                                                                                                                                              │
│ --is-humanoid    --no-is-humanoid          [default: is-humanoid]                                                                                                                                                                                                                       │
│ --alignment                          TEXT  [default: None]                                                                                                                                                                                                                              │
│ --help                                     Show this message and exit.                                                                                                                                                                                                                  │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Notice how now _all_ the options have a default.


### `unset`

The `unset` command is used to return a settings value to its initial state. If the value has a default, it will be set
to that value. If it does not have a default, it will simply be removed. Like the `update` subcommand, `unset` allows
the settings to be in invalid state.

Each settings value from the settings model is mapped to a CLI option that `takes no value`. If you supply the option,
then the corresponding setting value will be unset.

The help text from our example above for the `unset` subcommand looks like this:

```text
$ python examples/settings/commands.py settings unset --help

 Usage: commands.py settings unset [OPTIONS]

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --name                                                                                                                                                                                                                                                                                  │
│ --planet                                                                                                                                                                                                                                                                                │
│ --is-humanoid                                                                                                                                                                                                                                                                           │
│ --alignment                                                                                                                                                                                                                                                                             │
│ --help                 Show this message and exit.                                                                                                                                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```


### `show`

The `show` command displays the current settings. It validates settings while loading them, so validators that inspect
an encrypted secret may prompt for the passphrase.


### `reset`

The `reset` command returns _all_ settings values to their initial state. It allows the settings to be in an invalid
state when it is finished. It will also show the new settings values when it is done. The `reset` subcommand takes no
arguments.


## Nested settings models

It is possible to have your settings model include nested pydantic models for the settings values. If the settings model
has nested models, the arguments to `bind` and `update` should be JSON strings.

Consider this example:

```python {linenums="1"}
--8<-- "examples/settings/nested.py"
```

With such a settings configuration, you would bind your settings with a command like:

```text
$ python examples/settings/nested.py settings bind \
  --name=jawa \
  --planet='{"name": "tatooine", "climate": "desert"}' \
  --coloration='{"eyes": "yellow", "hair": "black"}'

╭─ Current settings ───────────────────────────────────────────────────────────╮
│                                                                              │
│ Settings Values                                                              │
│                                                                              │
│         name  str          ->  jawa                                          │
│       planet  Planet*      ->  name='tatooine' climate='desert'              │
│   coloration  Coloration*  ->  eyes='yellow' hair='black'                    │
│  is-humanoid  bool         ->  True                                          │
│    alignment  str          ->  neutral                                       │
│                                                                              │
│                                                                              │
│                                                                              │
│ *Nested Model Types                                                          │
│                                                                              │
│  Planet(name=str climate=str)                                                │
│  Coloration(eyes=str hair=str)                                               │
│                                                                              │
╰─ saved to /home/dusktreader/.local/share/settings-nested-example/settings...─╯
```

You can see that the nested model types are noted at the bottom including the expected types for each field.


## Secret settings values

Some settings values are sensitive — API tokens, passwords, private keys — and should not be displayed in plain text
when running `settings show`. `typerdrive` provides two types for these values, both of which are subclasses of
Pydantic's [`SecretStr`](https://docs.pydantic.dev/latest/concepts/types/#secret-types):

- `PlaintextSecretStr`: masked for display, and stored as plaintext in the settings file
- `EncryptedSecretStr`: masked for display, and encrypted at rest

!!! warning "Do not use Pydantic's `SecretStr` in settings models"

    Pydantic serializes `SecretStr` to a mask (`**********`) in JSON, so a settings file saved with a plain `SecretStr`
    field would contain the mask instead of the value, and the real value would be lost. `typerdrive` does not detect
    this, and `SecretStr` is not supported in settings models. Always use `PlaintextSecretStr` or `EncryptedSecretStr`
    instead.


### Annotating a field as secret

Use `PlaintextSecretStr` for a value that should be masked in settings output, or `EncryptedSecretStr` for a value that
should also be encrypted at rest:

```python
from pydantic import BaseModel, ConfigDict, Field
from typerdrive import EncryptedSecretStr, PlaintextSecretStr


class AppSettings(BaseModel):
    model_config = ConfigDict(validate_default=True)

    username: str = Field(default="", description="Your username")
    password: PlaintextSecretStr = Field(
        default=PlaintextSecretStr(""), description="Masked but stored as plaintext"
    )
    api_token: EncryptedSecretStr = Field(
        default=EncryptedSecretStr(""), description="Masked and encrypted at rest"
    )
```

!!! warning "Always validate defaults for secret fields"

    Pydantic does not validate field defaults by default, so a bare string default stays a plain `str` instead of
    being converted to a secret type. A bare `str` has no `.get_secret_value()` which typerdrive uses to get the
    unmasked value of the secret. So, if you use a normal `str` as the default for a secret, the value is not masked in
    output and is persisted as-is. An `EncryptedSecretStr` field with a bare string default would be written to disk
    **unencrypted**.

    There are three ways to avoid this issue:

    1. Set `validate_default=True` in the model config so that defaults are converted to the secret type:
       ```python
       class AppSettings(BaseModel):
           model_config = ConfigDict(validate_default=True)

           password: PlaintextSecretStr = "changeme"
       ```

    2. Set `validate_default=True` on the secret field itself:
       ```python
       class AppSettings(BaseModel):
           password: PlaintextSecretStr = Field(default="changeme", validate_default=True)
       ```

    3. Declare the default explicitly as `PlaintextSecretStr("...")` or `EncryptedSecretStr("...")`:
       ```python
       class AppSettings(BaseModel):
           password: PlaintextSecretStr = PlaintextSecretStr("changeme")
       ```

    To avoid overriding `pydantic` behaviors, `typerdrive` does not enforce any of these, so applications are
    responsible for choosing one approach.

Both types mask their values in settings output. `PlaintextSecretStr` only masks display; its value remains plaintext
on disk. `EncryptedSecretStr` also encrypts the field at rest and requires configured encryption material.


### Plaintext vs encrypted secrets

The two types differ only in how the value is handled on disk:

|                                                           | `PlaintextSecretStr` | `EncryptedSecretStr`              |
|-----------------------------------------------------------|----------------------|-----------------------------------|
| Masked in `settings show`, `str()`, and `repr()`          | yes                  | yes                               |
| Value read with `.get_secret_value()`                     | yes                  | yes (may prompt for a passphrase) |
| Written to the settings file as                           | plaintext            | age ciphertext (`age:...`)        |
| Requires the `encrypt-secrets` extra and encryption setup | no                   | yes                               |

Use `PlaintextSecretStr` when masking the value in output is enough, since the settings file is only accessible to the
current user. Use `EncryptedSecretStr` when the value must not be readable from the settings file; see
[Encrypting secret settings values](#encrypting-secret-settings-values) for setup and how it works.


### Display masking

When `settings show` (or any other settings subcommand) renders the settings table, both `PlaintextSecretStr` and
`EncryptedSecretStr` fields are automatically masked:

```text
$ myapp settings show

╭─ Current settings ────────────────────────────────────────────────────────────╮
│                                                                               │
│ Settings Values                                                               │
│                                                                               │
│   username   str                 ->  leia                                     │
│   password   PlaintextSecretStr  ->  **********                               │
│   api-token  EncryptedSecretStr  ->  **********                               │
│                                                                               │
╰───────────────────────────────────────────────────────────────────────────────╯
```


### Persistence

`PlaintextSecretStr` values are stored in plain text. The settings file is protected with appropriate filesystem
permissions: it is written so that it is readable and writable only by the current user. Fields annotated `EncryptedSecretStr` are encrypted instead; see
[Encrypting secret settings values](#encrypting-secret-settings-values).

```json
{
  "username": "leia",
  "password": "my-secret-password"
}
```

The settings file is typically `~/.local/state/<app-name>/settings.json`, though the location follows `XDG_STATE_HOME`
and can be changed in the [config](../config.md). Because it is only accessible to the current user, other users cannot read it, but anything running as that user (including backups of the
file) can see `PlaintextSecretStr` values and other unencrypted settings in plaintext. Use `EncryptedSecretStr`, or manage
secrets outside `typerdrive` (such as in a system keychain or environment variable), if this does not meet your
security requirements.


### Accessing the value in your commands

Because both types inherit from Pydantic's `SecretStr`, call `.get_secret_value()` to obtain the raw string when using
either value in your application code:

```python
import typer
from typerdrive.settings import attach_settings

@cli.command()
@attach_settings(AppSettings)
def call_api(ctx: typer.Context, settings: AppSettings):
    token = settings.api_token.get_secret_value()
    # use token with your HTTP client ...
```


### Encrypting secret settings values

There are some finer details for `EncryptedSecretStr` covered in this section. Encrypted secrets protect values on disk
by encrypting them at rest with an age X25519 recipient. See
[Plaintext vs encrypted secrets](#plaintext-vs-encrypted-secrets) for how it compares to `PlaintextSecretStr`.


#### How it works

Encryption uses [age](https://age-encryption.org). An age key pair has two halves:

- The **recipient** is the public half. It can only be used to encrypt, so it is safe to have around.
- The **identity** is the private half. It is required to decrypt, so it must be kept secret.

When settings are saved, each `EncryptedSecretStr` value is encrypted for the recipient and written to the settings
file as a string that starts with `age:`. The settings file never contains the plaintext. Saving only needs the
recipient, but reading a value back needs the identity.

The identity is stored by typerdrive, and there are two ways to protect it:

- **Passphrase protected** (the default): the identity is itself encrypted with a passphrase that you choose. Your
  secrets are never encrypted with the passphrase directly. Instead, the passphrase unlocks the identity, and the identity
  decrypts your secrets. This means that changing the passphrase only re-protects the identity; the encrypted settings
  values stay exactly as they are.
- **Passwordless**: the identity is stored without protection, so it never prompts. See
  [Passwordless identity](#passwordless-identity) for the tradeoffs.

To avoid prompting for the passphrase on every access, an unlocked identity is remembered for a short time. See
[Identity cache and security limits](#identity-cache-and-security-limits).


#### Setup

Install the optional dependency:

```shell
pip install 'typerdrive[encrypt-secrets]'
```

Encryption is selected by the field type: `EncryptedSecretStr` fields are encrypted separately using an age X25519
recipient, while `PlaintextSecretStr` fields remain plaintext. Set the cache lifetime during app startup if needed:

```python
from typerdrive import set_typerdrive_config

set_typerdrive_config(encryption_cache_ttl=300)
```

Encryption also requires setup of the app's encryption material. Existing plaintext values in an `EncryptedSecretStr`
field are read as before and migrate to encrypted values on the next settings save. Previously created files and backups
may still contain plaintext. Loading encrypted settings without the appropriate encryption material fails rather than
silently exposing or overwriting them.

Every settings save containing encrypted secrets verifies access to the matching identity before writing. A locked
passphrase-protected identity prompts for its passphrase; a valid cached unlock avoids repeat prompts. The save verifies
retained ciphertext too, even when the encrypted value was not changed. Passwordless identities require the same
verification but do not prompt for a passphrase.

Use the settings commands registered by `add_settings_subcommand()` to manage the encryption material:

- `myapp settings encryption setup`: create encryption material with a passphrase by default.
- `myapp settings encryption setup --no-passphrase`: create material with an unprotected identity instead.
- `myapp settings encryption change-passphrase`: rewrap a passphrase-protected identity with a new passphrase.
- `myapp settings encryption lock`: remove the cached identity.
- `myapp settings encryption unlock`: verify the passphrase and cache the identity when caching is enabled.
- `myapp settings encryption reset`: remove the identity and reset all encrypted settings values to their defaults, so
  that you can start over (asks for confirmation).

The encryption identity is created and managed by typerdrive; you never need to handle it directly. By default, it is
protected by the passphrase you choose, so keep that passphrase safe. Changing the passphrase does not re-encrypt the
settings values. Setup never replaces an existing identity.

If the passphrase or the identity is lost, the encrypted values cannot be recovered. To start over, run
`myapp settings encryption reset`. This removes the identity and resets every encrypted settings value to its default
(other settings are untouched). Then run `myapp settings encryption setup` again and re-enter the secrets. The
`myapp settings reset` command also removes the identity, since it removes all settings.

Encrypted secrets decrypt lazily when application code or a validator calls `get_secret_value()`. For a
passphrase-protected identity, the call prompts if no usable cached identity exists. Display masking itself does not
require decryption, but `settings show` can prompt if a validator inspects an encrypted secret while loading settings.


#### Passwordless identity

As an explicit alternative to passphrase protection, create a passwordless identity during initial setup:

```shell
myapp settings encryption setup --no-passphrase
```

This stores the private identity without any passphrase protection, readable only by the current user. Encrypted
settings saves still verify the identity, but a passwordless identity needs no passphrase prompt. Anyone who can read
the identity can decrypt your secrets, including other processes running as the same user and anyone with access to
file or account backups. You are responsible for protecting your backups.

#### Identity cache and security limits

For passphrase-protected material, `encryption_cache_ttl` is the identity cache lifetime in seconds and defaults to
`300`. Set it to `0` to disable caching; unlocking then verifies the passphrase but does not retain the identity for
later access. When caching is enabled, the unwrapped identity is stored in plaintext under the app's cache directory, typically
`~/.cache/<app-name>/secret-encryption-identity.json` (the location follows `XDG_CACHE_HOME` and can be changed in the
[config](../config.md)). This file is separate from the app cache managed by the
`cache` commands, and is only readable by the current user.

Expiration is checked on access, not by a background process: an expired plaintext cache file remains on disk until the
next access removes it. `encryption lock` removes the cache file. File deletion does not guarantee secure erasure from
the filesystem, snapshots, backups, or memory, and interrupted writes can leave private temporary files. Restrict
filesystem access and consider these limits when deciding whether to enable caching.


#### Validating encrypted secrets

Pydantic validators can inspect an encrypted secret with `get_secret_value()` and return the original secret object:

```python
from pydantic import BaseModel, ConfigDict, field_validator
from typerdrive import EncryptedSecretStr


class AppSettings(BaseModel):
    model_config = ConfigDict(validate_default=True)

    api_token: EncryptedSecretStr

    @field_validator("api_token")
    @classmethod
    def validate_token(cls, value: EncryptedSecretStr) -> EncryptedSecretStr:
        if not value.get_secret_value().startswith("token_"):
            raise ValueError("Invalid token format")
        return value
```

Normal settings loads, updates, and explicit validation can run validators and prompt for a passphrase when an encrypted
secret is inspected. This includes `settings show` during loading. Saves independently verify the identity, even when no
validator inspects a secret. A usable cached identity avoids the prompt; with a zero TTL, each save or decryption can
prompt. Passwordless identities require no passphrase. Avoid including plaintext secrets in validation errors or logs.
Validators that replace or discard encrypted secret objects can change persistence behavior; applications are responsible
for preserving the intended encryption path.


#### Encryption constraints and platforms

On settings saves, `SettingsManager` serializes the model with Pydantic and passes a serialization context that tells
each secret type how to write itself: `EncryptedSecretStr` values are written as ciphertext and `PlaintextSecretStr`
values as plaintext. Because the types serialize themselves, this works for secrets in nested models and collections.
Outside of a settings save, both types are masked when serialized to JSON.

Custom serializers, aliases, untyped or extra fields, and copying or transforming model values may change or bypass
that path. `typerdrive` does not reject every such pattern; applications are responsible for ensuring that sensitive
values reach persistence through the intended encrypted field and for checking their serialized output.

The optional `pyrage` dependency has wheels for macOS and for Linux on x64 and arm64. Windows x64 wheels are also
available, but the settings feature does not currently support Windows.


## The `get_settings()` functions

In order for `typerdrive` to provide the settings through an argument to the command function, we have to tap into a bit
of Python and Typer's "mystical energy field". If you want to use something more direct, you can access the settings
object using the `get_settings()` function to extract it from the `typer.Context` instead. Rewriting the `report()`
command to use the `get_settings()` function would look like this:

```python
@cli.command()
@attach_settings(SettingsModel)
def report(ctx: typer.Context):
    cfg = get_settings(ctx, SettingsModel)
    print(
        unwrap(
            f"""
            Look at this {cfg.alignment} {cfg.name} from {cfg.planet}
            {'walking' if cfg.is_humanoid else 'slithering'} by.
            """
        )
    )
```

!!!note "The `type_hint` argument to `get_settings()`"

```text
Because the model is bound to the settings commands _dynamically_, the `get_settings()` function needs a type hint
to cast it to the appropriate model type. This `type_hint` argument must match with the settings model that was
attached or an exception will be raised.
```


## The `add_.*()` functions

The `typerdrive.settings.commands` module has several `add_.*()` functions. These work by adding a subcommand to the CLI
app that is passed in. In general, you only need to use the `add_settings_subcommand()` in your app. However, if you
want to customize where the settings subcommands appear, you may call the other `add_.*()` functions directly


### `add_bind()`

This method adds the `bind` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

[Function Reference](../reference/settings.md/#typerdrive.settings.commands.add_bind)


### `add_update()`

This method adds the `update` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

[Function Reference](../reference/settings.md/#typerdrive.settings.commands.add_update)


### `add_unset()`

This method adds the `unset` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

[Function Reference](../reference/settings.md/#typerdrive.settings.commands.add_unset)


### `add_show()`

This method adds the `show` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

[Function Reference](../reference/settings.md/#typerdrive.settings.commands.add_show)


### `add_reset()`

This method adds the `reset` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

[Function Reference](../reference/settings.md/#typerdrive.settings.commands.add_reset)


### `add_settings_subcommand()`

This method does three things:

- Creates a new Typer app
- Adds all the settings subcommands to the new app
- Adds the new app as a subcommand of the Typer CLI that you provide

The result is that all the subcommands are available under one `settings` subcommand.

[Function Reference](../reference/settings.md/#typerdrive.settings.commands.add_settings_subcommand)
