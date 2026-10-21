# Typerdrive configuration

Typerdrive uses its own config for app identity and the behavior of its built-in features.


## Overview

When you build an app with Typerdrive, there are two kinds of configuration to keep straight.

`TyperdriveConfig` tells Typerdrive how to behave and what to display about your app, such as its name, version, and
description. The `settings` feature is for values that your app uses to control
its behavior outside of what typerdrive provides out of the box.

For example, `TyperdriveConfig` controls how long Typerdrive retains logs. When you build an app on top of typerdrive,
you might need your app to remember the user's home planet. In that case, you will use the builtin `settings` feature to
remember the planet name. Typerdrive knows about log files and storage, but
it doesn't know anything about planets; that's part of your app's logic.


## Usage

### Set configuration

`set_typerdrive_config()` is usually called during app setup, before Typer invokes
the CLI. It accepts keyword arguments for the values the app wants to override.

```python {linenums="1"}
--8<-- "examples/config/info.py"
```

The example sets app metadata and logging/output options before creating the CLI. The config stays in
memory for the current process; it does not write or replace the app's settings file.


### Inspect configuration

`add_info_subcommand()` adds the `info` and `version` commands to a Typer app. `info` shows app metadata; `info --full`
shows every config value and computed storage path. `version` prints `<app_name> v<version>` by default, or `<app_name>
(version unknown)` if no version is configured. `version --terse` prints
only the version string, or `unknown` when no version is configured.

When we run the `info` example, we see the compact app info:

```text
$ python examples/config/info.py info

+- App Information --------------------------------------------------------------------------------+
|                                                                                                  |
| Name         config-example                                                                      |
| Version      1.2.3                                                                               |
| Description  Demonstrate Typerdrive configuration.                                               |
|                                                                                                  |
+--------------------------------------------------------------------------------------------------+
```

When we run `info` example with the `--full` flag, the full `TyperdriveConfig` is shown:

```text
$ python examples/config/info.py info --full

+- Typerdrive Config ------------------------------------------------------------------------------+
|                                                                                                  |
|                                                                                                  |
|   Setting                Value                                                                   |
|  ────────────────────────────────────────────────────────────────────────────────                |
|   app_name               config-example                                                          |
|   version                1.2.3                                                                   |
|   description            Demonstrate Typerdrive configuration.                                   |
|   log_file_rotation      1 week                                                                  |
|   log_file_retention     1 month                                                                 |
|   log_file_compression   tar.gz                                                                  |
|   log_file_name          config-example.log                                                      |
|   console_width          100                                                                     |
|   console_ascii_only     True                                                                    |
|   state_home             /tmp/typerdrive-docs-state                                              |
|   cache_home             /tmp/typerdrive-docs-cache                                              |
|   log_dir                /tmp/typerdrive-docs-state/config-example/logs                          |
|   settings_path          /tmp/typerdrive-docs-state/config-example/settings.json                 |
|   cache_dir              /tmp/typerdrive-docs-cache/config-example                               |
|   files_dir              /tmp/typerdrive-docs-state/config-example/files                         |
|   database_path          /tmp/typerdrive-docs-state/config-example/db.sqlite                     |
|                                                                                                  |
|                                                                                                  |
+--------------------------------------------------------------------------------------------------+
```


### Show the app version

We can show the app's version info with the `version` command:

```text
$ python examples/config/info.py version
config-example v1.2.3
```

The terse version command prints just the version:

```text
$ python examples/config/info.py version --terse
1.2.3
```


## Details

### Configuration values

`app_name` defaults to the executable name derived from `sys.argv[0]`. `version` and `description` default to `None`.

| Value                  | Default          | Purpose                                                            |
| ---------------------- | ---------------- | ------------------------------------------------------------------ |
| `app_name`             | Executable name  | Identifies the client app and scopes its Typerdrive data.          |
| `version`              | `None`           | Client app version displayed by `info` and `version`.              |
| `description`          | `None`           | Short client app description displayed by `info`.                  |
| `log_file_rotation`    | `1 week`         | Loguru rotation policy for log files.                              |
| `log_file_retention`   | `1 month`        | Loguru retention policy for log files.                             |
| `log_file_compression` | `tar.gz`         | Compression format for rotated logs.                               |
| `log_file_name`        | `app.log`        | Name of the managed log file.                                      |
| `console_width`        | `None`           | Fixed Rich console width; `None` uses the terminal width.          |
| `console_ascii_only`   | `False`          | Use ASCII borders instead of Unicode borders in Typerdrive output. |
| `state_home`           | `XDG_STATE_HOME` | Base directory for state files and logs.                           |
| `cache_home`           | `XDG_CACHE_HOME` | Base directory for cache data.                                     |


### Computed storage paths

Typerdrive computes storage paths from `app_name`, `state_home`, and `cache_home`:

| Value           | Path                                    |
| --------------- | --------------------------------------- |
| `log_dir`       | `<state_home>/<app_name>/logs`          |
| `settings_path` | `<state_home>/<app_name>/settings.json` |
| `files_dir`     | `<state_home>/<app_name>/files`         |
| `database_path` | `<state_home>/<app_name>/db.sqlite`     |
| `cache_dir`     | `<cache_home>/<app_name>`               |

By default, `state_home` uses `XDG_STATE_HOME` (usually `~/.local/state`) and `cache_home` uses `XDG_CACHE_HOME`
(usually `~/.cache`). Setting either field overrides its corresponding XDG directory. The `settings_path` is where
Typerdrive stores the app settings feature; it is not a replacement for the app's own settings model.


### API reference

See the [base module reference](../reference/base_modules.md) for
the `TyperdriveConfig` model and `set_typerdrive_config()` API.
