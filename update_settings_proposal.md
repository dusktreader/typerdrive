# Proposal: `update_settings` convenience helper

## Problem

Updating settings from inside a command currently requires importing and
interacting with `SettingsManager` directly:

```python
from typerdrive import get_settings_manager

manager = get_settings_manager(ctx)
manager.update(**values)
settings = cast(MySettings, manager.settings_instance)
```

`get_settings()` already provides a clean, typed way to read the settings instance
without touching the manager. There is no equivalent for writes. Commands that
only need to push key/value updates shouldn't have to import or hold a reference
to the manager at all.


## Proposed change

Add a single function to `settings/attach.py`:

```python
def update_settings(ctx: typer.Context, **values: Any) -> None:
    """
    Update settings values via the manager bound to the context.
    """
    get_settings_manager(ctx).update(**values)
```

Export it from `typerdrive/__init__.py` alongside `get_settings`,
`get_settings_value`, and `get_settings_manager`.


## Usage

With `update_settings` and the existing `get_settings`, a downstream call site
goes from:

```python
from typerdrive import get_settings_manager

manager = get_settings_manager(ctx)
manager.update(**updates)
settings = cast(MySettings, manager.settings_instance)
```

to:

```python
from typerdrive import get_settings, update_settings

update_settings(ctx, **updates)
settings = get_settings(ctx, MySettings)
```

No cast, no manager import. `get_settings` already returns the narrowed type via
its `type_hint` parameter.


## Files touched

| File | Change |
|------|--------|
| `settings/attach.py` | Add `update_settings` function (~5 lines) |
| `__init__.py` | Add `update_settings` to imports and `__all__` (2 lines) |


## Relationship to the generic `SettingsManager` proposal

This is independent of (and complementary to) the generic `SettingsManager[ST]`
proposal in `generic_manager_proposal.md`. Even after `SettingsManager` becomes
generic, `update_settings` remains useful because it keeps downstream commands
from needing to import or reference the manager at all. The two changes pair well
but neither depends on the other.
