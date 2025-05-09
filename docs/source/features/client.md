# API Clients with some special modifications

More sophisticated CLI applications often need to talk to one or more remote APIs. To help you with that, `typerdrive`
includes a client that can be attached to any command using the `@attach_client()`. The client can load its
configuration from the settings if they are attached.

Additionally, the client provided by `typerdrive` has some specialized features called the `*_x()` methods that provide
some useful scaffolding around the standard [`httpx`](https://www.python-httpx.org) query functions.


## Overview

The `typerdrive` package provides the `@attach_client()` decorator that allows you to access instances of
`TyperdriveClient` as arguments to your command function. The `TyperdriveClient` inherits from `httpx.Client` and adds
the following enhancements through the `*_x()` methods:

- Ability to specify the query parameters as a `pydantic` model instance
- Ability to specify the request body as a `pydantic` model instance
- Ability to provide an expected status (an exception will be raised if it does not match)
- Ability to provide a `pydantic` model class to deserialize the response into

The `@attach_client()` decorator also makes it easy to initialize the instances of the `TyperdriveClient` using values
from your settings model provided through `@attach_settings()`.


## Usage

Let's look at a code example to see how the `@attach_client()` decorator and `TyperdriveClient` can be used:

```python {linenums="1"}
--8<-- "examples/client/attach.py"
```

In this example, we are attaching two separate clients that both connect to the
[Star Wars API (SWAPI)](https://swapi.info). Both clients utilize a base url provided in the settings. Finally, both
clients are accessed in the command function body by providing a `TyperdriveClient` argument with a name that matches
the keyword arguments in `@attach_client()`.

When we run the example, the two clients will load some data from the API and show it on the screen:

```
$ python examples/client/attach.py

╭─ Person 1 ───────────────────────────────────────────────────────────────────╮
│                                                                              │
│   name='Luke Skywalker' height=172 birth_year='19BBY' gender='male'          │
│                                                                              │
╰─ Fetched from https://swapi.info/api/people/1 ───────────────────────────────╯


╭─ Planet 1 ───────────────────────────────────────────────────────────────────╮
│                                                                              │
│   name='Tatooine' climate='arid' terrain='desert' gravity='1 standard'       │
│   population=200000                                                          │
│                                                                              │
╰─ Fetched from https://swapi.info/api/planets/1 ──────────────────────────────╯
```

As you can see, because client requests included a `response_model` keyword argument, the returned data was
automatically deserialized into the provided `pydantic` model.

The client also provides error checking that can work hand-in-hand with the `@handle_errors()` decorator so that if the
request provides the wrong response code, response data type, or incorrectly formatted data you can have a helpful error
message provided to your users:

```
$ python examples/client/attach.py --person-id=9000

╭─ Lookup on SWAPI failed! ────────────────────────────────────────────────────╮
│                                                                              │
│   Got an unexpected status code: Expected 200, got 404 -- Not Found          │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

In this case, we attempted to fetch a person that doesn't exist on `SWAPI`, consequently, the server returned a `404: Not
Found` response. Since our request specified that a 200 was to be expected, an error was raised. That error was neatly
handled by the `@handle_errors()` decorator and presented nicely to the user.


## Details

There are some important details to know about with the `TyperdriveClient` and the `@attach_client()` decorator that
we'll go over now.


### `TyperdriveClient`

The `TyperdriveClient` is a very thin layer over the top of a normal `httpx.Client` instance. However, the `*_x()`
methods provide a lot of extra functionality that, in my experience, are very nice to have when working with APIs in a
CLI app.

Let's go over the methods.


#### `TyperdriveClient.__init__()`

There is only one additional keyword argument added that the base `httpx.Client` doesn't have. It's the `log_func`
parameter. If provided, the `TyperdriveClient` will use this function to log its behavior as it's processing a request.
This is very useful for debugging issues with the requests.

This parameter can be any function that acts on a string, but usually you would use a method from a `logging.Logger`,
just the builtin `print` function, or (as I usually prefer) a `loguru.Logger` method. If it is not provided, the
`TyperdriveClient` will use a builtin logger named `typerdrive.client` and log all its messages at a `DEBUG` level.

[Method Reference](../../reference/#typerdrive.client.base.TyperdriveClient.__init__)


#### `TyperdriveClient.request_x()`

This is the beating heart of the `TyperdriveClient`. The function will issue a request using `httpx.Client.request()`,
but it provides a lot of functionality that is controlled by it's keyword arguments.

The `TyperdriveClient` accepts all the same args and kwargs as it's parent `httpx.Client` (and passes them along at init
time), but also accepts additional kwargs.

[Method Reference](../../reference/#typerdrive.client.base.TyperdriveClient.request_x)


##### `param_obj`

If provided, this should be an instance of a `pydantic` model. It will be deserialized into a dictionary that will be
used for the request URL parameters. Suppose that a `GET` endpoint in your API supports query params `page`,
`page_size`, `sort`, and `search`. You could use a pydantic model to describe the params like this:

```python {linenums="1"}
class Params(BaseModel):
    page: int = 0
    page_size: int = 10
    sort: bool = False
    search: str = ""
```

and use an instance of it in your request:

```python {linenums="1"}
client = TyperdriveClient()
client.request_x("GET", "/cities/mos-eisley", param_obj=Params(sort=True, search="droids"))
```

If user input is going to be used to drive the url parameters, using a `pydantic` model provides a very convenient
validation mechanism.


##### `body_obj`

Like the `param_obj`, the `body_obj` parameter allows you to use an instance of a `pydantic` model to describe the body
of the request that will be sent. Let's suppose now, that you have a `POST` endpoint that requires a specific format of
data to create a new entity. You can use `pydantic` to structure and validate the data and let the `TyperdriveClient`
correctly deserialize the data for its request.

Suppose the endpoint needs a JSON structure like this in the `POST` request:

```json
{
  "external": {
    "casing": "durasteel",
    "buttons": 1
  },
  "internal": {
    "kyber_crystal": "green",
    "emitter_shape": "cup"
  }
}
```

Then, you might have `pydantic` models set up like this:

```python {linenums="1"}
class ExternalParts(BaseModel):
    casing: str = "steel"
    buttons: int = 1

class InternalParts(BaseModel):
    kyber_crystal: Color
    emitter_shape: "cup"

class Lightsaber(BaseModel):
    internal: InternalParts
    external: ExternalParts
```

Finally, we could make our request using `request_x()` like this:

```python {linenums="1"}
lightsaber_3 = Lightsaber(
    internal=InternalParts(kyber_crystal=GREEN),
    external=ExternalParts(casing="durasteel"),
)
client.request_x("POST", "/lightsaber", body_obj=lightsaber_3)
```


##### `expected_status`

If this parameter is provided, then the return status code from the request will be compared against this value. If it
does not match, an exception will be raised.


##### `expect_response`

This flag indicates whether or not the request is expected to return a response. By default, the `request_x()` method
expects to receive a JSON response from the server. If you know that the endpoint you are calling doesn't return a
response, then you can pass `expect_response=False`, and the `request_x()` method will return the status code from the
request only:

```python {linenums="1"}
client.request_x("DELETE", "/death-star/tractor-beam", expect_response=False)
```


##### `response_model`

This is probably the most useful feature of the `TyperdriveClient`. If you provide a `pydantic` model class with the
`response_model` parameter, then the `request_x()` method will deserialize the response into an instance of that model.
If deserialization fails, an exception will be raised explaining what went wrong.

Consider an API endpoint that returns a payload like this:

```json
{
    "total_amount": 17000,
    "up_front": 2000,
    "on_delivery": 15000,
    "extras": "safe delivery"
}
```

We could create a model describing what we expect to receive from the API and use it in the request:

```python {linenums="1"}
class TransportAgreement(BaseModel):
   total_amount: int
   up_front: int
   on_delivery: int
   extras: str | None

client.request_x("POST", "/smuggler", response_model=TransportAgreement)
```


#### `TyperdriveClient.get_x()`

This method simply calls `request_x()` with a fixed method of `GET`.

[Method Reference](../../reference/#typerdrive.client.base.TyperdriveClient.get_x)


#### `TyperdriveClient.post_x()`

This method simply calls `request_x()` with a fixed method of `POST`.

[Method Reference](../../reference/#typerdrive.client.base.TyperdriveClient.post_x)


#### `TyperdriveClient.put_x()`

This method simply calls `request_x()` with a fixed method of `PUT`.

[Method Reference](../../reference/#typerdrive.client.base.TyperdriveClient.put_x)


#### `TyperdriveClient.patch_x()`

This method simply calls `request_x()` with a fixed method of `PATCH`.

[Method Reference](../../reference/#typerdrive.client.base.TyperdriveClient.patch_x)


#### `TyperdriveClient.delete_x()`

This method simply calls `request_x()` with a fixed method of `DELETE`.

[Method Reference](../../reference/#typerdrive.client.base.TyperdriveClient.delete_x)


### `attach_client()`

The `attach_client()` decorator is used to bind instances of `TyperdriveClient` to the command context. It instantiates
the client instances.

It does this by mapping the keyword arguments (besides `log_func`) to new client instances.

The keyword argument name will be the name of the newly created client. The value of the keyword argument is used to
provide a `base_url` for the new client. The `attach_client()` decorator will first try to match the value with a
settings value if the settings are attached to the context. If it can't find a matching settings value, then it will use
the value itself as a `base_url`.

Consider this example:

```python {linenums="1"}

class SettingsModel(BaseModel):
    people_api: str = "https://swapi.info/api/people"

cli = typer.Typer()

@cli.command()
@attach_settings(SettingsModel)
@attach_client(people="people_api")
def report(ctx: typer.Context, people: TyperdriveClient):
    ...
```

Here, the settings contain a value "people_api" that matches the _value_ of the keyword argument. Thus, a new
`TyperdriveClient` instance named "people" is created and bound to the context. Because we provided a parameter named
`people` to the `report()` function, the new client will be available in the function body as a variable named `people`.


Let's look at a different example:

```python {linenums="1"}
class SettingsModel(BaseModel):
    people_api: str = "https://swapi.info/api/people"

cli = typer.Typer()

@cli.command()
@attach_settings(SettingsModel)
@attach_client(planets="https://swapi.info/api/planets")
def report(ctx: typer.Context, planets: TyperdriveClient):
    ...
```

Because the _value_ of the keyword argument to `@attach_client()` doesn't match any settings, the value will be used as
the `base_url` for the "planets" client in the function body.

Finally, let's look at one more example:

```python {linenums="1"}
cli = typer.Typer()

@cli.command()
@handle_errors("Lookup on SWAPI failed!")
@attach_client(planets="planets_api")
def report(ctx: typer.Context, planets: TyperdriveClient):
    ...
```

In this case, we don't have a settings object bound. On its own, that won't be a problem. However, because no settings
value can be matched to "planets_api", that value would be used for a `base_url`. Since "planets_api" is not a valid
http/https URL, however, an exception will be raised:

```
╭─ Lookup on SWAPI failed! ────────────────────────────────────────────────────╮
│                                                                              │
│   Couldn't use base_url='planets_url' for client. If using a settings key,   │
│   make sure settings are attached.                                           │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

Finally, it should be noted that if you pass a `log_func` value to the `@attach_client()` decorator, this will be passed
to each client instance to use to log its work.

[Function Reference](../../reference/#typerdrive.client.attach.attach_client)
