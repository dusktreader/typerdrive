# Proposal: Generic `SettingsManager` and `update_settings` helper

## Problem

`SettingsManager` stores the model class and instance typed as bare `BaseModel`:

```python
class SettingsManager:
    settings_model: type[BaseModel]
    settings_instance: BaseModel
```

Any code that pulls the instance out of the manager loses the concrete type. Call
sites are forced to `cast()`:

```python
manager = get_settings_manager(ctx)
manager.update(**updates)
settings = cast(CrolTrollSettings, manager.settings_instance)
```

`get_settings()` works around this by accepting a `type_hint` argument, but there
is no equivalent for updating settings without importing the manager directly.


## Proposed changes

### 1. Make `SettingsManager` generic (manager.py)

Four annotation changes, zero runtime changes:

```python
# before
class SettingsManager:
    settings_model: type[BaseModel]
    settings_instance: BaseModel

    def __init__(self, settings_model: type[BaseModel]):
        ...

# after
class SettingsManager[ST: BaseModel]:
    settings_model: type[ST]
    settings_instance: ST

    def __init__(self, settings_model: type[ST]):
        ...
```

Every method body stays identical. `construct_permissive` in `utilities.py` is
already generic, so it needs no changes.


### 2. Thread the type variable through `attach_settings` (attach.py)

The decorator signature picks up a type variable so the manager it constructs
carries the concrete type:

```python
# before
def attach_settings(
    settings_model: type[BaseModel],
    ...
) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:

# after
def attach_settings[ST: BaseModel](
    settings_model: type[ST],
    ...
) -> Callable[[ContextFunction[P, T]], ContextFunction[P, T]]:
```

Inside the wrapper:

```python
# before
manager: SettingsManager = SettingsManager(settings_model)

# after
manager: SettingsManager[ST] = SettingsManager(settings_model)
```

### 3. Add `update_settings` helper (attach.py)

A small companion to `get_settings` that applies updates without forcing callers
to import and interact with the manager:

```python
def update_settings(ctx: typer.Context, **values: Any) -> None:
    """
    Update settings values via the manager bound to the context.
    """
    get_settings_manager(ctx).update(**values)
```

Export it from `typerdrive/__init__.py` alongside `get_settings`.


### 4. `get_settings_manager` return type

The manager is stashed in the typer context as `Any`, so there is no way to
recover the type parameter at retrieval time. Two options:

**Option A (recommended):** Leave `get_settings_manager` returning
`SettingsManager[BaseModel]` (equivalent to today's unparameterized form). Callers
that need the narrowed type use `get_settings()` for reads and `update_settings()`
for writes. No API breakage.

**Option B:** Add a `type_hint` parameter:

```python
def get_settings_manager[ST: BaseModel](
    ctx: typer.Context,
    type_hint: type[ST],
) -> SettingsManager[ST]:
```

This is a breaking change to the function signature. Probably not worth it since
`get_settings()` + `update_settings()` cover the use cases without exposing the
manager.


## What changes in downstream projects

With Option A and the new `update_settings` helper, a call site like this in
crol-troll's `init()`:

```python
from typerdrive import get_settings_manager

# ...
if updates:
    manager = get_settings_manager(ctx)
    manager.update(**updates)
    settings = cast(CrolTrollSettings, manager.settings_instance)
```

becomes:

```python
from typerdrive import get_settings, update_settings

# ...
if updates:
    update_settings(ctx, **updates)
    settings = get_settings(ctx, CrolTrollSettings)
```

No casts, no manager import, and `settings` is typed as `CrolTrollSettings`.


## Files touched

| File | Change | Scope |
|------|--------|-------|
| `settings/manager.py` | Add `[ST: BaseModel]` to class, 2 attrs, `__init__` param | 4 annotation lines |
| `settings/attach.py` | Add `[ST: BaseModel]` to `attach_settings`, type `manager`, add `update_settings` | ~8 lines |
| `settings/__init__.py` | No changes needed (empty) | -- |
| `__init__.py` | Export `update_settings` | 2 lines |

Runtime behavior is completely unchanged. This is a pure type-annotation
improvement plus one small convenience function.
