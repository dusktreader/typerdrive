# Commands to manage application cache

Because basic `Typer` apps are essentially stateless, there isn't a good way to temporarily store data. A cache can be
useful when you want to keep data between sessions, but the functionality of your app isn't dependent on the data
staying there. Auth tokens are a great example of this. If your app authenticates against an identity provider, you
probably don't want to have to login every time you run a command in your app.

A cache allows you to store your tokens between commands. Because you can always get new tokens by logging in again,
they fit well with the ephemeral nature of a cache.

To provide this functionality, `typerdrive` provides a cache manager and the `cache` subcommand to manage your app's
cache.


## Overview

The `typerdrive` package provides the functionality to store, retrieve, and clear three types of data:

- binary data
- text data
- json data

To gain access to your cache, you can retrieve the `CacheManager` that is bound to the user context through the use of
the `@attach_cache` decorator.

You can also view your cache at any time and clear one or all of the data in it through `cache` subcommands.


## Usage

It's useful to start with a code example to see the cache in action:

```python {linenums="1"}
--8<-- "examples/cache/commands.py"
```

In this toy example, some text is stored in the cache to be used for future executions of the `report` command.

If the data isn't in the cache yet, it's "loaded". The data is printed and then stored in the cache for future use:

```
$ python examples/cache/commands.py report
Cache miss! Loading text...
╭──────────────────────────────────────────────────────────────────────────────╮
│ Size matters not. Look at me. Judge me by my size, do you? Hmm? Hmm. And     │
│ well you should not. For my ally is the Force, and a powerful ally it is.    │
│ Life creates it, makes it grow. Its energy surrounds us and binds us.        │
│ Luminous beings are we, not this crude matter. You must feel the Force       │
│ around you; here, between you, me, the tree, the rock, everywhere, yes. Even │
│ between the land and the ship.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
Stored text at cache target yoda/speech.txt
```

When you run the command again, the data is retrieved from the cache instead:

```
$ python examples/cache/commands.py report
Cache hit! Loaded text from cache target yoda/speech.txt
╭──────────────────────────────────────────────────────────────────────────────╮
│ Size matters not. Look at me. Judge me by my size, do you? Hmm? Hmm. And     │
│ well you should not. For my ally is the Force, and a powerful ally it is.    │
│ Life creates it, makes it grow. Its energy surrounds us and binds us.        │
│ Luminous beings are we, not this crude matter. You must feel the Force       │
│ around you; here, between you, me, the tree, the rock, everywhere, yes. Even │
│ between the land and the ship.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

This time, the data was found in the cache so it was loaded from there.

Running the command a few more times will eventually store all the speeches in the cache. Now, you can view the cache if
to see what has been saved in it:

```
$ python examples/cache/commands.py cache show
╭─ Current cache ──────────────────────────────────────────────────────────────╮
│                                                                              │
│ 📂 /home/dusktreader/.cache/commands.py                                      │
│ ├── 📂 han                                                                   │
│ │   └── 📄 speech.txt (313 Bytes)                                            │
│ ├── 📂 leia                                                                  │
│ │   └── 📄 speech.txt (594 Bytes)                                            │
│ └── 📂 yoda                                                                  │
│     └── 📄 speech.txt (395 Bytes)                                            │
│                                                                              │
╰─ Storing 1.3 kB in 3 files ──────────────────────────────────────────────────╯
```

Let's say that we only want to remove a single item from the cache. We can do that using the `clear` command with a path
for the cache item. In this case, let's remove yoda's speech:

```
$ python examples/cache/commands.py cache clear --path=yoda/speech.txt

╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│   Cleared entry at cache target yoda/speech.txt                              │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

Let's view the cache again to verify that the file was removed:

```
$ python examples/cache/commands.py cache show

╭─ Current cache ──────────────────────────────────────────────────────────────╮
│                                                                              │
│ 📂 /home/dusktreader/.cache/commands.py                                      │
│ ├── 📂 han                                                                   │
│ │   └── 📄 speech.txt (313 Bytes)                                            │
│ └── 📂 leia                                                                  │
│     └── 📄 speech.txt (594 Bytes)                                            │
│                                                                              │
╰─ Storing 907 Bytes in 2 files ───────────────────────────────────────────────╯
```

Great! Now, we could go through and clean the remaining files up one at a time. But, the `clear` command will empty the
whole cache out if you run it without a specific path:

```
$ python examples/cache/commands.py cache clear
Are you sure you want to clear the entire cache? [y/N]: y

╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│   Cleared all 2 files from cache                                             │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

Note that you have to confirm whenever you request to clear the entire cache to prevent accidental deletion.


## Details

Let's take a closer look at the details of each `cache` subcommand and the methods of the `CacheManager`:


### `clear`

The `clear` command gives you the ability to remove items from the cache. You can target a specific entry in the cache
by passing it a specific path using the `--path` option. If the item is not found in the cache at that location, an
error will be raised. If it is found, the item will be deleted.

If no path is provided to the `clear` command, then the entire cache will be cleared out. You are required to confirm
your action to make sure that mistakes are not made.

The help text from the `clear` command looks like this:

```
$ python examples/cache/commands.py cache clear --help

 Usage: commands.py cache clear [OPTIONS]

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path        TEXT  Clear only the entry matching this path. If not provided,│
│                     clear the entire cache [default: None]                   │
│ --help              Show this message and exit.                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```


### `show`

The `show` command just shows the current state of the cache. It will show the entire tree structure of the data stored
in the cache and a report about how big the cache is and how many files are stored in it.


### `CacheManager.resolve_path()`

This method converts a cache target path like `yoda/speech.txt` into the absolute path to the file where the data is
stored. It does several checks to make sure that the file exists and that the resolved path is actually within the cache
directory (to prevent sneaky use of `..`).

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:108:108"
```


### `CacheManager.store_bytes()`

This method stores binary data in a cache target. An optional `mode` keyword argument can be provided to control the
permissions of the cache entry. So, for example, if you want only your user to be able to read and write to the entry,
you might use a `mode` of `0o600`.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:125:125"
```


### `CacheManager.store_text()`

This method stores text data in a cache target. It can also be given a `mode` parameter.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:133:133"
```


### `CacheManager.store_json()`

This method stores a dictionary of data in a cache target. The dictionary must be JSON serializable or an error will be
thrown. The JSON written to the file is formatted to be human readable. This method can also be provided a `mode`
parameter.

Function signature:

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:136:136"
```


### `CacheManager.load_bytes()`

This method loads binary data from a cache target. If the cache target does not exist, an error will be thrown.

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:139:139"
```


### `CacheManager.load_text()`

This method loads text data from a cache target. If the cache target does not exist, an error will be thrown.

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:145:145"
```


### `CacheManager.load_json()`

This method loads a JSON serialized dictionary from a cache target. If the cache target does not exist, an error will be
thrown. If the data at the cache target cannot be serialized, an error will be thrown.

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:148:148"
```


### `CacheManager.clear_path()`

This method removes an entry from the cache at the provided target. If the target does not exist, an error will be
thrown. If the parent directory of the entry is empty after it is removed, the parent directory will be removed as well.

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:153:153"
```


### `CacheManager.clear_all()`

This method will remove all items from the cache.

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:162:162"
```


### `CacheManager.pretty()`

This (poorly named) method gathers information about the cache and returns it in a format that can be pretty-printed by
the `@attach_cache` decorator.

```python {linenums="1"}
--8<-- "src/typerdrive/cache/manager.py:166:166"
```
