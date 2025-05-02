# User-friendly Error Handling

By default, `Typer` doesn't produce user-friendly errors. It does use
[`rich`](https://github.com/Textualize/rich) to add some style to the exceptions out of the box. But, without any other
error handling, your users will be confronted with a stack-trace and exception message that might be very difficult for
them to interpret.


## Overview

The `typerdrive` package provides a convenient way to handle errors within your Typer app. Instead of slapping your
users with a big stack-trace, `typerdrive` presents errors in a clean and friendly presentation so users can better
understand what went wrong.

```
╭─ Login Error ────────────────────────────────────────────────────────────────╮
│                                                                              │
│   Couldn't log you in to https://wretched-hive-of-scum-and-villainy.com      │                                                      │
│                                                                              │
╰─ If the problem persists, please contact tech support ───────────────────────╯
```

You can customize what errors are handled, which are ignored, and even add tasks that should be run by the error
handler.

The implementation of the `@handle_errors()` decorator was heavily influenced by the implementation of the
`handle_errors()` context manager from the
[`py-buzz` package](https://dusktreader.github.io/py-buzz/features/#exception-handling-context-manager), and so it uses
a lot of the same patterns.

The `TyperdriveError` (and subclasses) provided in `typerdrive` is a subclass of the
[`Buzz`](https://dusktreader.github.io/py-buzz/reference/#buzz.base.Buzz) class from `py-buzz`. If you want to learn
more about how to use `Buzz` classes, please checkout the linked documentation for `py-buzz`.


## Usage

Let's start out by looking at an example that uses the `@handle_errors()` decorator:

!!!warning "This one's more complicated!"

    This example is a bit more complicated because there's more setup needed to show the full breadth of the
    `@handle_errors()` decorator. The meat of the command function starts on line 49.

```python {linenums="1"}
--8<-- "examples/exceptions/handle_errors.py"
```

This example command simulates a coin flip where an exception is raised any time the outcome of the coin flip doesn't
match the user's guess. This provides a nice way to see how the error handling works with a single command.

Let's try it out:

```
$ python examples/exceptions/handle_errors.py tails

╭─ Tada! ──────────────────────────────────────────────────────────────────────╮
│                                                                              │
│   tails, you win!                                                            │
│                                                                              │
╰─ Maybe you won't be so lucky next time! ─────────────────────────────────────╯
```

Ok, so on my first try, I guessed correctly, and a message was displayed for to tell me I won.

Great, let's try again and see what happens:

```
$ python examples/exceptions/handle_errors.py tails

╭─ Womp, womp ─────────────────────────────────────────────────────────────────╮
│                                                                              │
│   heads, you lose!                                                           │
│                                                                              │
╰─ Don't sweat it; just try again! ────────────────────────────────────────────╯
```

So this time I lost, and again a message is showt to let me know. However, this time the function doesn't explicitly
print the message. Instead, it raises a `TyperdriveError` which is handled by the `@handle_errors()` decorator instead.

No stack trace is shown to the user and the message that is displayed has none of the trappings of an exception message.
Instead, it's clear and simple so the user will understand what is going on.

The great power of this error handling is that a `TyperdriveError` that is raised in any code that is _called_ by the command
function will also be caught and presented nicely to the user.

Next, let's try the command with the `--show-logs` option that is available:

```
$ python examples/exceptions/handle_errors.py tails --show-logs
2025-04-25 17:48:54,680: DEBUG -> Result: tails

╭─ Tada! ──────────────────────────────────────────────────────────────────────╮
│                                                                              │
│   tails, you win!                                                            │
│                                                                              │
╰─ Maybe you won't be so lucky next time! ─────────────────────────────────────╯

2025-04-25 17:48:54,682: INFO -> No errors occurred!
2025-04-25 17:48:54,682: INFO -> Program complete. Exiting.
```

I won again this time, but this time I get to see the app's logs. Notice that in the function body, there is only one
logging statement to log the result. However, we have passed three parameters to the `@handle_errors()` decorator that
each log some data.

Because I won, only the functions provided with the  `do_else` and `do_finally` options are actually called. Both of
these functions take no parameters and simply log a message. Regardless of whether an exception was raised or not, any
provided `do_finally` function will be called after the command function returns. The `do_else` option will only be
triggered if no exceptions were raised in the function body.

Let's try another flip:

```
$ python examples/exceptions/handle_errors.py tails --show-logs
2025-04-25 17:52:37,977: DEBUG -> Result: heads
2025-04-25 17:52:37,978: ERROR -> Flip error -- TyperdriveError: heads, you lose!
--------
Traceback:
  File "/home/dusktreader/git-repos/personal/typerdrive/src/typerdrive/exceptions.py", line 69, in wrapper
    return_value = func(*args, **kwargs)
  File "/home/dusktreader/git-repos/personal/typerdrive/examples/exceptions/handle_errors.py", line 62, in flip
    raise TyperdriveError(
    ...<3 lines>...
    )


╭─ Womp, womp ─────────────────────────────────────────────────────────────────╮
│                                                                              │
│   heads, you lose!                                                           │
│                                                                              │
╰─ Don't sweat it; just try again! ────────────────────────────────────────────╯

2025-04-25 17:52:37,980: INFO -> Program complete. Exiting.
```

This time I lost again, and a lot more information was logged. The `do_except` function is triggered whenever an
exception is handled by the `@handle_errors()` decorator. The function is passed a special argument which is an instance
of the `DoExceptParams` data class provided by the `py-buzz` package. This argument carries with it some detailed
information about the handled error. In this case, our `log_error()` function uses the stack trace contained in the
param to show a traceback of the handled error in the logs.

All three of the `do_.*` parameters are useful, but the `do_except` parameter is the most powerful because you can do
some post-processing on the error any time one is handled.

It's worth pointing out here that this example doesn't tell the `@handle_errors()` decorator what kind of exceptions it
should handle. By default, `@handle_errors()` will only handle instances of `TyperdriveError` or one of its descendants. If
you want to handle a different exception type (or any of its descendants), you can provide it in the `handle_exc_class`
keyword argument. If, for instance, you wanted the handler to catch any and all errors that might be raised in the
command function, you could pass `handle_exc_class=Exception` to the decorator.


## Details

Now, let's dive a little deeper into the details of the `@handle_errors()` decorator.


### `base_message`

This is the `base_message` that will be included with the final message that is passed in the `DoExceptParams` that are
passed to the `do_except` function. This base message can be overridden by setting the `subject` on a `TyperdriveError` (or
exception class derived from it. When the error message is displayed for the user, the `base_message` is the text that
is used for the "subject" (also known as "title") of the panel that the exception's message will be displayed inside of.
This parameter is required.

This parameter is an analog of the
[`base_message`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.handle_errors) parameter used in the
`handle_errors()` context manager from `py-buzz`.


### `handle_exc_class`

This keyword argument identifies the exception type that will be handled by the `@handle_errors()` decorator. Any
exception that is an instance of this type or an instance of any class that inherits from it will be handled. By
default, this kwarg is set to `TyperdriveError` exception class. It is also possible to provide a `tuple` of exception types
that should be handled by the decorator.

This parameter is an analog of the
[`handle_exc_class`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.handle_errors) parameter used in the
`handle_errors()` context manager from `py-buzz`.


### `ignore_exc_class`

This kwarg is only useful when combined with `handle_exc_class`. It identifies an exception type that should _not_ be
handled by the `@handle_errors()` decorator even if it is a subclass of the exception type passed to `handle_exc_class`.
This is useful to selectively omit specific exception types from handling. This is particularly important if you set
`handle_exc_class=Exception` and you still need to let certain exception types escape. Like `handle_exc_class`, this can
be passed a `tuple` of exception types each of which will be ignored.

This parameter is an analog of the
[`ignore_exc_class`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.handle_errors) parameter used in the
`handle_errors()` context manager from `py-buzz`.


### `do_except`

This keyword argument provides a function that will be called anytime an exception is handled by the
`@handle_errors()` decorator. The function provided in this kwarg _must_ take exactly one argument of type
[`DoExceptParams`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.DoExceptParams). `DoExceptParams` is a
dataclass that carries specific information about the handled error including:

- `err`: The exception itself
- `base_message`: As [described above](#base_message)
- `final_message`: A formatted string that include the exception name, `base_message`, and `err` message.
- `trace`: A traceback of the error

The `do_except` kwarg is most useful for providing a function that will log details about the error without overwhelming
your user with this information.

This parameter is an analog of the
[`do_except`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.handle_errors) parameter used in the
`handle_errors()` context manager from `py-buzz`.


### `do_else`

This kwarg provides a function that will be called only if no (unhandled) exceptions were raised in the command function
body. This function can take no arguments. It is not nearly as powerful as the `do_except` argument, it may be useful to
carry out some task that should only happen if no errors were encountered.

This parameter is an analog of the
[`do_else`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.handle_errors) parameter used in the
`handle_errors()` context manager from `py-buzz`.


### `do_finally`

This keyword argument provides a function that will be called no matter what happens in the command function's body. It
does not matter if an exception was raised or not, this function will be called after the command function returns.
Again, this kwarg is not as powerful as the `do_except` option. But it can have its uses, especially when you need to do
some cleanup after the command completes.

This parameter is an analog of the
[`do_finally`](https://dusktreader.github.io/py-buzz/reference/#buzz.tools.handle_errors) parameter used in the
`handle_errors()` context manager from `py-buzz`.


### `unwrap_message`

By default, the `@handle_errors()` decorator will unwrap the message that is passed to it. That is, it will first dedent
the message then join all the lines together. This is useful because a longer message is often passed in the form of
a triple-quoted text block that is optimized for viewing the code. However, we don't know how wide the user's monitor
will be. Thus, it's better to let `rich` do the wrapping for us.

However, sometimes the error message has a particular structure to it with indents and newlines. This is the case with
`Pydantic` validation errors. In this case, we don't want the message unwrapped to a single line. If you set the
`unwrap_message` kwarg to `False` the error will be printed as-is.
