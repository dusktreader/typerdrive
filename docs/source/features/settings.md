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
`@attach_settings` decorator adds the settings object to the app's `typer.Context`. Then, the `get_settings()` function
can be called to retrieve an instance of the `SettingsModel` from the app context.

!!!note "Passing `type_hint` to `get_settings()`"

    You don't _have_ to pass a type_hint to `get_settings()` for the code to work. However, static type checkers will
    object if you try to assign the returned model instance to your specific settings model. Because the model is bound
    to the settings commands _dynamically_, the `get_settings()` function needs a type hint to cast it to the
    appropriate model type.

Great, now let's try a few commands in this app to see how the settings commands work.

First, we will just show the config

```
$ python examples/settings/commands.py settings show

╭─ Current settings ──────────────────────────────────────────────────────────────────────────╮
│                                                                                             │
│   is-humanoid -> True                                                                       │
│     alignment -> neutral                                                                    │
│                                                                                             │
│   Configuration is invalid:                                                                 │
│          name -> Field required                                                             │
│        planet -> Field required                                                             │
│                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

As you can see, our settings initially just matches the defaults provided in the settings model.  The fields that still
need to be defined are clearly identified and the settings are shown to be invalid.

Next, let's make the settings valid by setting the missing values with `bind`:

```
╭─ Current settings ──────────────────────────────────────────────────────────────────────────╮
│                                                                                             │
│          name -> jawa                                                                       │
│        planet -> tatooine                                                                   │
│   is-humanoid -> True                                                                       │
│     alignment -> neutral                                                                    │
│                                                                                             │
╰─ saved to /home/dusktreader/.local/share/commands.py/settings.json ─────────────────────────╯
```

Now, the settings are valid. You can also see that the settings were saved to disk for your app to use in future
commands.

Let's make an adjustment to the settings using the `update` command:

```
$ python examples/settings/commands.py settings update --name=hutt --no-is-humanoid

╭─ Current settings ──────────────────────────────────────────────────────────────────────────╮
│                                                                                             │
│          name -> hutt                                                                       │
│        planet -> tatooine                                                                   │
│   is-humanoid -> False                                                                      │
│     alignment -> neutral                                                                    │
│                                                                                             │
╰─ saved to /home/dusktreader/.local/share/commands.py/settings.json ─────────────────────────╯
```

Notice that the `update` command only changed the values specified and left the others alone.

Now that we're happy with our settings, lets run our `report` command to try out using these app settings:

```
$ python examples/settings/commands.py report
Look at this neutral hutt from tatooine slithering by.
```

Great! Our app is able to use the settings in any command!

Finally, let's clear out the settings with `reset`:

```

╭─ Current settings ──────────────────────────────────────────────────────────────────────────╮
│                                                                                             │
│   is-humanoid -> True                                                                       │
│     alignment -> neutral                                                                    │
│                                                                                             │
│   Configuration is invalid:                                                                 │
│          name -> Field required                                                             │
│        planet -> Field required                                                             │
│                                                                                             │
╰─ saved to /home/dusktreader/.local/share/commands.py/settings.json ─────────────────────────╯
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

!!!note "Not supported on Windows"

    Currently, the `typerdrive` `settings` commands are only configured to work on Linux and MacOS. I have plans to add
    support for Windows as well eventually, but at the moment `typerdrive` is dependent on settings being stored below
    `~/.local/share`

Each settings value from the settings model you provide is mapped to a CLI option for the `bind` subcommand. If the
value has a default in the model, then the option will use the same default. Boolean values use the normal convention
from Typer with `--flag` or `--no-flag` controlling the value of the boolean.

The help text from our example above for the `bind` subcommand looks like this:

```
$ python examples/settings/commands.py settings bind --help

 Usage: commands.py settings bind [OPTIONS]

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --name                               TEXT  [default: None] [required]                                                                                                                                                                                                                │
│ *  --planet                             TEXT  [default: None] [required]                                                                                                                                                                                                                │
│    --is-humanoid    --no-is-humanoid          [default: is-humanoid]                                                                                                                                                                                                                    │
│    --alignment                          TEXT  [default: neutral]                                                                                                                                                                                                                        │
│    --help                                     Show this message and exit.                                                                                                                                                                                                               │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
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

```
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

```
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

The `show` command just shows the current value of the settings. That's it!


### `reset`

The `reset` command returns _all_ settings values to their initial state. It allows the settings to be in an invalid
state when it is finished. It will also show the new settings values when it is done. The `reset` subcommand takes no
arguments.


## The `add_.*()` functions

The `typerdrive.settings.commands` module has several `add_.*()` functions. These work by adding a subcommand to the
CLI app that is passed in. In general, you only need to use the `add_settings_subcommand()` in your app. However, if you
want to customize where the settings subcommands appear, you may call the other `add_.*()` functions directly


### `add_bind()`

This method adds the `bind` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/settings/commands.py:23:23"
```


### `add_update()`

This method adds the `update` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/settings/commands.py:71:71"
```


### `add_unset()`

This method adds the `unset` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/settings/commands.py:120:120"
```


### `add_show()`

This method adds the `show` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/settings/commands.py:162:162"
```


### `add_reset()`

This method adds the `reset` subcommand to the provided CLI app. It uses the
[`build_command()`](https://dusktreader.github.io/typer-repyt/build_command/) function to dynamically create a command
and then adds it to the `cli` argument.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/settings/commands.py:193:193"
```


### `add_settings_subcommand()`

This method does three things:

- Creates a new Typer app
- Adds all the settings subcommands to the new app
- Adds the new app as a subcommand of the Typer CLI that you provide

The result is that all the subcommands are available under one `settings` subcommand.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/settings/commands.py:218:218"
```


