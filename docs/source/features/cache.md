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

The `typerdrive` package provides a high-performance, disk-based cache using the `diskcache` library. The cache can
store any Python object that can be pickled, including:

- binary data
- text data
- dictionaries and lists
- Pydantic models
- custom Python objects

To gain access to your cache, you can retrieve the `CacheManager` that is bound to the user context through the use of
the `@attach_cache` decorator by providing an argument to your command with the `CacheManager` type.

!!!note "The type is important!"

    The type for your "manager" argument must be `CacheManager`, or Typer will throw an error!

You can also view your cache at any time, delete specific entries, or clear groups of entries through `cache`
subcommands.


## Usage

It's useful to start with a code example to see the cache in action:

```python {linenums="1"}
from datetime import timedelta
import typer
from typerdrive import attach_cache, CacheManager

cli = typer.Typer()

@cli.command()
@attach_cache()
def store_data(ctx: typer.Context, manager: CacheManager):
    # Store simple values
    manager.set("api_token", "secret-token-12345")

    # Store with expiration (1 hour)
    manager.set("session", {"user": "jedi_master"}, expire=timedelta(hours=1))

    # Store with groups for organizing related entries
    manager.set("user:123:profile", {"name": "Yoda"}, group="user_data")
    manager.set("user:456:profile", {"name": "Obi-Wan"}, group="user_data")

    print("Data stored in cache!")

@cli.command()
@attach_cache()
def load_data(ctx: typer.Context, manager: CacheManager):
    token = manager.get("api_token")
    session = manager.get("session", default={})

    print(f"Token: {token}")
    print(f"Session: {session}")
```


### Adding Cache Commands to Your CLI

To add the cache subcommand to your CLI:

```python
from typerdrive import add_cache_subcommand

cli = typer.Typer()
add_cache_subcommand(cli)

# Now your CLI has:
# - cache show [--group] [--stats]
# - cache clear [--group]
```


### Viewing the cache

You can view the current cache contents using the `cache show` command:

```
$ python my_app.py cache show
Cache contains 4 entries:

  Key                Group       TTL        
 ───────────────────────────────────────── 
  api_token                      never      
  session                        58 minutes 
  user:123:profile   user_data   never      
  user:456:profile   user_data   never      

```

The TTL (Time To Live) column shows when each entry will expire in human-readable format:
- `never` - No expiration set
- `2 hours`, `30 minutes`, etc. - Time remaining until expiration
- `expired` - Entry no longer exists or has expired


### Filtering by group

You can filter the cache view by group to see related entries:

```
$ python my_app.py cache show --group=user_data
Cache contains 2 entries (group=user_data):

  Key                Group       TTL   
 ──────────────────────────────────── 
  user:123:profile   user_data   never 
  user:456:profile   user_data   never 

```


### Viewing cache statistics

You can view cache statistics using the `--stats` flag:

```
$ python my_app.py cache show --stats
Cache Statistics:

  Metric           Value 
 ─────────────────────── 
  Size (entries)   4     
  Volume (bytes)   1024  
  Hits             12    
  Misses           3     

```


### Clearing by group

To remove all entries with a specific group, use the `cache clear` command with the `--group` option:

```
$ python my_app.py cache clear --group=user_data
Cleared 2 entries with group 'user_data'
```


### Clearing the entire cache

To clear all cache entries, run `cache clear` without any options. You'll be asked to confirm:

```
$ python my_app.py cache clear
Are you sure you want to clear the entire cache? [y/N]: y
Cleared 4 entries from cache
```


## Details

Let's take a closer look at the details of each `cache` subcommand and the methods of the `CacheManager`:


### `cache` sub-commands

The `cache` command provides two sub-commands to manage the cache.


#### `clear`

The `clear` command removes multiple entries from the cache. You can use it in two ways:

1. **Clear by group**: Remove all entries with a specific group using `--group`
2. **Clear all**: Remove all cache entries (requires confirmation)

The help text from the `clear` command looks like this:

```
$ python my_app.py cache clear --help

 Usage: my_app.py cache clear [OPTIONS]

 Remove multiple entries from the cache.

╭─ Options ───────────────────────────────────────────────────────────────────────╮
│ --group        TEXT  Clear only entries with this group. If not provided, clear │
│                      entire cache                                               │
│ --help               Show this message and exit.                                │
╰─────────────────────────────────────────────────────────────────────────────────╯
```


#### `show`

The `show` command displays cache contents or statistics. It supports filtering by group:

```
$ python my_app.py cache show --help

 Usage: my_app.py cache show [OPTIONS]

 Show cache contents or statistics.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --group        TEXT  Filter entries by group                                 │
│ --stats              Show cache statistics instead of entries                │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```


### The `get_cache_manager()` function

The `attach` submodule of `typerdrive.cache` provides a `get_cache_manager()` function. If you want to avoid the magic
of using a parameter to your command with the `CacheManager` type, you can get access to the `CacheManager` instance
from the `typer.Context` using the `get_cache_manager()` function instead.


### `CacheManager` methods

The `CacheManager` provides several methods for interacting with the cache.


#### `CacheManager.__init__()`

Initialize the cache manager with optional configuration:

- `size_limit`: Maximum size of cache in bytes (default: 1GB)
- `eviction_policy`: Policy for removing entries when size limit is reached (default:
  `EvictionPolicy.LEAST_RECENTLY_USED`)

```python
from typerdrive import CacheManager, EvictionPolicy

manager = CacheManager(
    size_limit=2**30,  # 1GB
    eviction_policy=EvictionPolicy.LEAST_RECENTLY_USED
)
```

Available eviction policies:
- `EvictionPolicy.LEAST_RECENTLY_USED`:   Remove least recently accessed items
- `EvictionPolicy.LEAST_FREQUENTLY_USED`: Remove least frequently accessed items
- `EvictionPolicy.NONE`:                  No automatic eviction (errors when full)

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.__init__)


#### `CacheManager.set()`

Store a value in the cache. The value can be any picklable Python object.

```python
from datetime import timedelta

# Simple value
manager.set("key", "value")

# With expiration
manager.set("session", {"user": "yoda"}, expire=timedelta(hours=1))

# With group for group assignment
manager.set("user:123", {"name": "Luke"}, group="users")
```

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.set)


#### `CacheManager.get()`

Retrieve a value from the cache. Returns the default value if the key doesn't exist or has expired.

```python
# Get with default
value = manager.get("key", default="not found")

# Get without default (returns None if not found)
value = manager.get("key")
```

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.get)


#### `CacheManager.setdefault()`

Get a value from the cache, or set and return a default value if the key doesn't exist. This is similar to Python's
`dict.setdefault()` method.

```python
# Get from cache, or set default if not found
token = manager.setdefault("api_token", "default-token")

# With expiration
session = manager.setdefault(
    "session",
    {"user": "guest"},
    expire=timedelta(hours=1)
)

# With group
data = manager.setdefault("data", [], group="temp_data")
```

This is more concise than using `get()` and `set()` separately:

```python
# Instead of:
value = manager.get("key")
if value is None:
    value = "default"
    manager.set("key", value)

# Use:
value = manager.setdefault("key", "default")
```

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.setdefault)


#### `CacheManager.delete()`

Remove a specific entry from the cache. Returns `True` if the key was deleted, `False` if it didn't exist.

```python
if manager.delete("old_key"):
    print("Key deleted")
else:
    print("Key not found")
```

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.delete)


#### `CacheManager.clear()`

Remove multiple entries from the cache. Can clear by group or clear everything.

```python
# Clear all entries with a specific group
count = manager.clear(group="temp_data")
print(f"Removed {count} entries")

# Clear all entries
count = manager.clear()
print(f"Removed {count} entries")
```

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.clear)


#### `CacheManager.keys()`

Get a list of cache keys, optionally filtered by pattern and/or group.

```python
# All keys
all_keys = manager.keys()

# Filter by regex pattern
user_keys = manager.keys(pattern=r"user:\d+")

# Filter by group
grouped_keys = manager.keys(group="sessions")

# Combine filters
filtered = manager.keys(pattern=r"user:.*", group="active")
```

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.keys)


#### `CacheManager.get_ttl()`

Get the time-to-live (TTL) for a cache key in human-readable format.

```python
# Check when an entry will expire
ttl = manager.get_ttl("api_token")
print(f"Token expires in: {ttl}")  # e.g., "2 hours" or "never"

# Check multiple entries
for key in manager.keys():
    ttl = manager.get_ttl(key)
    print(f"{key}: {ttl}")
```

Returns:
- `"never"` - Entry has no expiration
- `"2 hours"`, `"30 minutes"`, etc. - Human-readable time until expiration
- `"expired"` - Entry doesn't exist or has already expired

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.get_ttl)


#### `CacheManager.stats()`

Get cache statistics including hits, misses, size, and volume. Returns a `CacheStats` Pydantic model.

```python
stats = manager.stats()
print(f"Cache size: {stats.size} entries")
print(f"Cache volume: {stats.volume} bytes")
print(f"Cache hits: {stats.hits}")
print(f"Cache misses: {stats.misses}")
```

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.stats)


#### `CacheManager.show()`

Display cache contents or statistics in a formatted table. This is the programmatic equivalent of the `cache show`
command.

```python
# Show all entries
manager.show()

# Show with group filter
manager.show(group="active")

# Show statistics
manager.show(show_stats=True)
```

Note: The `pattern` parameter is available for programmatic use but not exposed in the CLI to avoid leaking
implementation details to end users.

[Method Reference](../reference/cache.md/#typerdrive.cache.manager.CacheManager.show)


## Use Cases


### Authentication Tokens

Cache authentication tokens to avoid repeated logins:

```python
from datetime import timedelta
import typer
from typerdrive import attach_cache, CacheManager

@cli.command()
@attach_cache()
def login(ctx: typer.Context, manager: CacheManager, username: str, password: str):
    # Authenticate and get token from identity provider
    token = authenticate(username, password)
    
    # Cache token for 8 hours
    manager.set("auth_token", token, expire=timedelta(hours=8))
    print("Login successful! Token cached.")

@cli.command()
@attach_cache()
def api_request(ctx: typer.Context, manager: CacheManager, endpoint: str):
    token = manager.get("auth_token")
    
    if token is None:
        print("Not authenticated. Please run 'login' first.")
        raise typer.Exit(1)
    
    # Use token for API request
    response = requests.get(endpoint, headers={"Authorization": f"Bearer {token}"})
    print(response.json())
```


### API Response Caching

Cache expensive API responses to reduce latency and API usage:

```python
from datetime import timedelta
import hashlib
import typer
from typerdrive import attach_cache, CacheManager

@cli.command()
@attach_cache()
def fetch_data(ctx: typer.Context, manager: CacheManager, query: str):
    # Create cache key from query
    cache_key = f"api_response:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
    
    # Try to get cached response
    cached = manager.get(cache_key)
    if cached is not None:
        print("Using cached response")
        return cached
    
    # Fetch from API
    print("Fetching from API...")
    response = expensive_api_call(query)
    
    # Cache for 15 minutes
    manager.set(cache_key, response, expire=timedelta(minutes=15), group="api_cache")
    return response

@cli.command()
@attach_cache()
def clear_cache(ctx: typer.Context, manager: CacheManager):
    count = manager.clear(group="api_cache")
    print(f"Cleared {count} cached API responses")
```


### Session Data

Store temporary session data across command invocations:

```python
from datetime import timedelta
import typer
from typerdrive import attach_cache, CacheManager

@cli.command()
@attach_cache()
def start_workflow(ctx: typer.Context, manager: CacheManager, project_id: str):
    session = {
        "project_id": project_id,
        "step": 1,
        "started_at": datetime.now().isoformat()
    }
    
    # Session expires after 2 hours of inactivity
    manager.set("workflow_session", session, expire=timedelta(hours=2))
    print(f"Started workflow for project {project_id}")

@cli.command()
@attach_cache()
def continue_workflow(ctx: typer.Context, manager: CacheManager):
    session = manager.get("workflow_session")
    
    if session is None:
        print("No active workflow session. Run 'start_workflow' first.")
        raise typer.Exit(1)
    
    # Update session
    session["step"] += 1
    manager.set("workflow_session", session, expire=timedelta(hours=2))
    
    print(f"Continuing workflow (step {session['step']})")

@cli.command()
@attach_cache()
def end_workflow(ctx: typer.Context, manager: CacheManager):
    if manager.delete("workflow_session"):
        print("Workflow session ended")
    else:
        print("No active workflow session")
```


### Rate Limiting

Track API usage to enforce rate limits:

```python
from datetime import timedelta, datetime
import typer
from typerdrive import attach_cache, CacheManager

@cli.command()
@attach_cache()
def call_api(ctx: typer.Context, manager: CacheManager, endpoint: str):
    # Track API calls in cache
    rate_limit_key = "api_calls_count"
    
    # Get current count (starts at 0)
    count = manager.setdefault(rate_limit_key, 0, expire=timedelta(hours=1))
    
    # Check rate limit (100 calls per hour)
    if count >= 100:
        ttl = manager.get_ttl(rate_limit_key)
        print(f"Rate limit exceeded. Resets in {ttl}")
        raise typer.Exit(1)
    
    # Increment count
    manager.set(rate_limit_key, count + 1, expire=timedelta(hours=1))
    
    # Make API call
    print(f"API call successful ({count + 1}/100)")
    # ... actual API call logic ...

@cli.command()
@attach_cache()
def check_limit(ctx: typer.Context, manager: CacheManager):
    count = manager.get("api_calls_count", default=0)
    ttl = manager.get_ttl("api_calls_count")
    print(f"API calls: {count}/100")
    print(f"Limit resets in: {ttl}")
```


### Computation Results

Cache expensive computation results:

```python
from datetime import timedelta
import typer
from typerdrive import attach_cache, CacheManager

@cli.command()
@attach_cache()
def analyze(ctx: typer.Context, manager: CacheManager, dataset: str, force: bool = False):
    cache_key = f"analysis:{dataset}"
    
    # Check cache unless force refresh
    if not force:
        cached = manager.get(cache_key)
        if cached is not None:
            print("Using cached analysis results")
            print_results(cached)
            return
    
    # Perform expensive analysis
    print("Running analysis (this may take a while)...")
    results = expensive_analysis(dataset)
    
    # Cache for 24 hours
    manager.set(cache_key, results, expire=timedelta(days=1), group="analysis")
    print_results(results)

@cli.command()
@attach_cache()
def list_analyses(ctx: typer.Context, manager: CacheManager):
    # Find all cached analyses
    keys = manager.keys(pattern=r"analysis:.*")
    
    print(f"Cached analyses ({len(keys)}):")
    for key in keys:
        dataset = key.split(":", 1)[1]
        ttl = manager.get_ttl(key)
        print(f"  - {dataset} (expires in {ttl})")
```


## Advanced Usage


### Working with expiring entries

You can set expiration times on cache entries using `timedelta`:

```python
from datetime import timedelta

# Expire after 1 hour
manager.set("api_token", "secret", expire=timedelta(hours=1))

# Expire after 30 seconds
manager.set("temp_data", {"foo": "bar"}, expire=timedelta(seconds=30))

# Expire after 7 days
manager.set("weekly_cache", data, expire=timedelta(days=7))
```


### Using groups for organization

Groups allow you to group related cache entries and manage them together:

```python
# Store multiple entries with the same group
manager.set("user:1:profile", {"name": "Luke"}, group="user_profiles")
manager.set("user:2:profile", {"name": "Leia"}, group="user_profiles")
manager.set("user:3:profile", {"name": "Han"}, group="user_profiles")

# Clear all user profiles at once
manager.clear(group="user_profiles")
```


### Cache size management

The cache automatically manages its size based on the configured eviction policy:

```python
from typerdrive import CacheManager, EvictionPolicy

# Create cache with 100MB limit
manager = CacheManager(
    size_limit=100 * 1024 * 1024,  # 100MB
    eviction_policy=EvictionPolicy.LEAST_RECENTLY_USED
)

# Cache will automatically evict old entries when limit is reached
for i in range(1000):
    manager.set(f"key_{i}", f"value_{i}" * 1000)
```


### Caching complex objects

The cache can store any picklable Python object:

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

# Store Pydantic model
user = User(name="Yoda", age=900)
manager.set("user:yoda", user)

# Retrieve it
cached_user = manager.get("user:yoda")
print(cached_user.name)  # "Yoda"
```


## Differences from Files

| Feature        | Cache                              | Files                              |
|----------------|------------------------------------|------------------------------------|
| **Purpose**    | Temporary storage                  | Persistent storage                 |
| **Durability** | Data may expire or be evicted      | Data persists indefinitely         |
| **Structure**  | Database (opaque)                  | File-based (can inspect manually)  |
| **Size limits**| Configurable size limits           | No automatic limits                |
| **Eviction**   | Automatic eviction policies        | Manual deletion only               |
| **Use for**    | Tokens, sessions, API responses    | Settings, templates, assets        |
