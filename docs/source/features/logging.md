# Managed logging with Loguru

Once your CLI has any degree of sophisitcation, you will probably want to include logging. Additionally, it may be
important to keep the logging output in a file (in a reasonable location). It is also important to be able to check the
logs, and remembering the reasonable location where the log file is locate can be tricky.

While the logging from the standard library is fairly good, I find that the
[`loguru`](https://loguru.readthedocs.io/en/stable/) logging package is so much nicer to work with. So, I built loguru
along with some other nice helpers into `typerdrive` to let you focus on building out the business logic of your CLI.


## Overview

The `typerdrive` package provides the `@attach_logging()` decorator to enable logging for the decorated command. It will
enable logging for the `typerdrive` internals and capture the logs in rotated log files. Additionally, if you include
the `verbose=True` flag in the `@attach_logging()` decorator, then the logs will also be printed to `stdout`.

In addition to the `@attach_logging()` decorator, `typerdrive` also includes three commands for viewing, auditing, and
clearing your logs.


## Usage

Again, let's look at a code example to see how the `@attach_client()` decorator can be used:

```python {linenums="1"}
--8<-- "examples/logging/attach.py"
```

In this example, we are simply looping some number of times and logging in each iteration. Once the loop is finished,
you will be shown the log file in a pager and, after you close that, a view of the contents of the log directory. The
final output from the function will look like this:

```
$ python examples/logging/attach.py report
15:55:39 | DEBUG | Logging attached to typer context
15:55:39 | INFO | Starting report
15:55:39 | INFO | Logging message 1
15:55:39 | INFO | Logging message 2
15:55:39 | INFO | Logging message 3
15:55:39 | INFO | Logging message 4
15:55:39 | INFO | Logging message 5
15:55:39 | INFO | Logging message 6
15:55:39 | INFO | Logging message 7
15:55:39 | INFO | Logging message 8
15:55:39 | INFO | Logging message 9
15:55:39 | INFO | Logging message 10
15:55:39 | INFO | Completing report
15:55:39 | INFO | Showing log
15:55:42 | INFO | Auditing log directory

╭─ Current log files ──────────────────────────────────────────────────────────╮
│                                                                              │
│ 📂 /home/dusktreader/.local/share/logging-attach-example/logs                │
│ └── 📄 app.log (1.2 kB)                                                      │
│                                                                              │
╰─ Storing 1.2 kB in 1 files ──────────────────────────────────────────────────╯
```


## Details

Let's take a closer look at the logging functionality available with `typerdrive`.


### `logs` sub-commands

The `logs` sub-commands can be enabled in your Typer CLI by calling the `add_logs_subcommand()`. This will enable the
following:


#### `show`

The `show` command opens the current log file in a [pager](https://en.wikipedia.org/wiki/Terminal_pager) for you to
peruse. Your system's pager will be used. Usually you can exit the pager by using the "q" key.


#### `audit`

The `audit` command shows the current state of the directory where the logs are stored. It will show the entire tree
structure of the directory and some information about how much data is being stored and how many files there are.


### `@attach_logging()` decorator

Logging in `typerdrive` is enabled for a command function through the use of the `@attach_logging()` decorator. There is
one optional argument available: `verbose`. If this flag is set, then all log lines of `DEBUG` and above will also be
printed to stdout. This should probably only be used for debugging issues in the application as it could potentially
bombard your user with a lot of finished.


### Configuration

By default, the log file will be rotated after one week, and log files older than one month will be deleted. Both of
these things are configurable using `typerdrive.config.set_typerdrive_config()`.


#### `log_file_rotation`

You can control how the log files are rotated using this key. It accepts the same values as the `rotation` parameter
used by [`loguru.logger.add()`](https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add). By
default, the files are rotated after one week.


#### `log_file_retention`

You can control how the log files are kept using this key. It accepts the same values as the `retention` parameter
used by [`loguru.logger.add()`](https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add). By
default, the files are deleted after one month.


#### `log_file_compression`

You can control how the log files are compressed upon rotation using this key. It accepts the same values as the
`compression` parameter used by
[`loguru.logger.add()`](https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add). By default,
the files are compressed to `tar.gz` files.


#### `log_file_name`

You can control the name of th log file using this key. By default, it will use "app.log".
