# Persistent File Storage

The `typerdrive` files feature provides a simple, persistent file storage system for your Typer CLI applications. Unlike
the cache (which is designed for ephemeral data), the files feature is meant for data that your application depends on
and should persist reliably.


## Overview

The files feature stores data in a directory structure within your application's data directory. Files are organized
using path-based keys (like `data/preferences.json` or `templates/email.txt`) and can store:

- Binary data (images, PDFs, archives, etc.)
- Text data (templates, logs, notes, etc.)
- JSON data (user preferences, cached API responses, etc.)

All files are stored in the `files_dir` location (typically `~/.local/share/<app_name>/files` on Linux,
`~/Library/Application Support/<app_name>/files` on macOS).


## Usage

### Basic Example

Here's a simple example showing how to store and load files:

```python
import typer
from typerdrive import attach_files, FilesManager

cli = typer.Typer()

@cli.command()
@attach_files()
def save_preferences(ctx: typer.Context, manager: FilesManager):
    preferences = {
        "theme": "dark",
        "editor": "vim",
        "auto_save": True
    }

    # Store as JSON
    manager.store_json(preferences, "user/preferences.json")
    print("Preferences saved!")

@cli.command()
@attach_files()
def load_preferences(ctx: typer.Context, manager: FilesManager):
    # Load JSON
    preferences = manager.load_json("user/preferences.json")
    print(f"Theme: {preferences['theme']}")
    print(f"Editor: {preferences['editor']}")

if __name__ == "__main__":
    cli()
```


### Adding Files Commands to Your CLI

To add the files subcommand to your CLI:

```python
from typerdrive import add_files_subcommand

cli = typer.Typer()
add_files_subcommand(cli)

# Now your CLI has:
# - files show
```


### Viewing Files

You can view the files directory structure using the `files show` command:

```bash
$ python my_app.py files show

╭─ Current files ──────────────────────────────────────────────────╮
│                                                                  │
│ 📂 /home/user/.local/share/my_app/files                          │
│ ├── 📂 user                                                      │
│ │   └── 📄 preferences.json (87 Bytes)                           │
│ ├── 📂 templates                                                 │
│ │   ├── 📄 email.txt (245 Bytes)                                 │
│ │   └── 📄 welcome.html (1.2 kB)                                 │
│ └── 📄 token.txt (128 Bytes)                                     │
│                                                                  │
╰─ Storing 1.6 kB in 4 files ──────────────────────────────────────╯
```


## Details

Let's take a closer look at the details of the `files` subcommand and the methods of the `FilesManager`:


### `files` sub-commands

The `files` command provides a sub-command to manage files.


#### `show`

Display the files directory structure and statistics.

```bash
$ python my_app.py files show
```

This command shows:
- The complete directory tree
- File sizes
- Total storage used
- Number of files


### The `@attach_files()` decorator

The `@attach_files()` decorator binds the `FilesManager` to your command's context. You can access it either through a
parameter or via `get_files_manager()`.

```python
from typerdrive import attach_files, FilesManager, get_files_manager

# Method 1: Using a parameter
@cli.command()
@attach_files()
def my_command(ctx: typer.Context, manager: FilesManager):
    manager.store_text("Hello!", "greeting.txt")

# Method 2: Using get_files_manager()
@cli.command()
@attach_files()
def my_command(ctx: typer.Context):
    manager = get_files_manager(ctx)
    manager.store_text("Hello!", "greeting.txt")

# Show files directory after command runs
@cli.command()
@attach_files(show=True)
def my_command(ctx: typer.Context, manager: FilesManager):
    manager.store_text("Hello!", "greeting.txt")
    # Files directory will be displayed automatically
```


### FilesManager Methods


#### `store_bytes(data, path, mode=None)`

Store binary data at the given path.

**Parameters:**
- `data` (bytes): The binary data to store
- `path` (Path | str): The file path (e.g., `"images/logo.png"`)
- `mode` (int | None): Optional file permissions (e.g., `0o600` for owner-only read/write)

**Example:**
```python
# Store an image
with open("logo.png", "rb") as f:
    image_data = f.read()
manager.store_bytes(image_data, "images/logo.png")

# Store with restricted permissions
manager.store_bytes(secret_data, "secrets/token", mode=0o600)
```


#### `store_text(text, path, mode=None)`

Store text data at the given path.

**Parameters:**
- `text` (str): The text to store
- `path` (Path | str): The file path (e.g., `"templates/email.txt"`)
- `mode` (int | None): Optional file permissions

**Example:**
```python
template = """
Hello {name},

Welcome to our service!
"""
manager.store_text(template, "templates/welcome.txt")
```


#### `store_json(data, path, mode=None)`

Store a dictionary as formatted JSON at the given path.

**Parameters:**
- `data` (dict): The dictionary to store (must be JSON serializable)
- `path` (Path | str): The file path (e.g., `"data/settings.json"`)
- `mode` (int | None): Optional file permissions

**Example:**
```python
api_settings = {
    "endpoints": {
        "primary": "https://api.example.com",
        "backup": "https://backup.api.example.com"
    },
    "timeout_seconds": 30
}
manager.store_json(api_settings, "data/api_settings.json")
```


#### `load_bytes(path)`

Load binary data from the given path.

**Parameters:**
- `path` (Path | str): The file path

**Returns:**
- `bytes`: The binary data

**Raises:**
- `FilesLoadError`: If the file doesn't exist or can't be read

**Example:**
```python
image_data = manager.load_bytes("images/logo.png")
with open("logo_copy.png", "wb") as f:
    f.write(image_data)
```


#### `load_text(path)`

Load text data from the given path.

**Parameters:**
- `path` (Path | str): The file path

**Returns:**
- `str`: The text content

**Raises:**
- `FilesLoadError`: If the file doesn't exist or can't be read

**Example:**
```python
template = manager.load_text("templates/welcome.txt")
message = template.format(name="Yoda")
```


#### `load_json(path)`

Load and parse JSON data from the given path.

**Parameters:**
- `path` (Path | str): The file path

**Returns:**
- `dict`: The parsed JSON data

**Raises:**
- `FilesLoadError`: If the file doesn't exist, can't be read, or contains invalid JSON

**Example:**
```python
api_settings = manager.load_json("data/api_settings.json")
primary_endpoint = api_settings["endpoints"]["primary"]
```


#### `delete(path)`

Delete a file at the given path. Empty parent directories are automatically removed.

**Parameters:**
- `path` (Path | str): The file path

**Returns:**
- `Path`: The full path of the deleted file

**Raises:**
- `FilesClearError`: If the file can't be deleted

**Example:**
```python
deleted_path = manager.delete("old/preferences.json")
print(f"Deleted: {deleted_path}")
print(f"Deleted: {deleted_path}")
```


#### `list_items(path)`

List all files (not directories) at the given path.

**Parameters:**
- `path` (Path | str): The directory path

**Returns:**
- `list[str]`: List of file names (not full paths)

**Raises:**
- `FilesError`: If the path doesn't exist or isn't a directory

**Example:**
```python
# List all templates
templates = manager.list_items("templates")
for template_name in templates:
    print(f"Template: {template_name}")
```


#### `resolve_path(path, mkdir=False)`

Resolve a file key to an absolute path within the files directory.

**Parameters:**
- `path` (Path | str): The file path
- `mkdir` (bool): If True, create parent directories if they don't exist

**Returns:**
- `Path`: The absolute path

**Raises:**
- `FilesError`: If the resolved path is outside the files directory

**Example:**
```python
full_path = manager.resolve_path("data/api_settings.json", mkdir=True)
print(f"Full path: {full_path}")
```


## Use Cases


### Application Settings

Store application settings that persist across runs:

```python
@cli.command()
@attach_files()
def setup(ctx: typer.Context, manager: FilesManager, api_key: str):
    settings = {
        "api_key": api_key,
        "configured_at": datetime.now().isoformat()
    }
    manager.store_json(settings, "app/settings.json")
    print("Settings saved!")

@cli.command()
@attach_files()
def status(ctx: typer.Context, manager: FilesManager):
    try:
        settings = manager.load_json("app/settings.json")
        print(f"Configured at: {settings['configured_at']}")
        print(f"API key: {settings['api_key'][:10]}...")
    except FilesLoadError:
        print("Not configured. Run 'setup' first.")
```


### Templates

Store and render templates:

```python
@cli.command()
@attach_files()
def send_email(ctx: typer.Context, manager: FilesManager, name: str):
    template = manager.load_text("templates/welcome.txt")
    message = template.format(name=name, date=datetime.now().strftime("%Y-%m-%d"))
    # Send email...
```


### Binary Assets

Store images, PDFs, or other binary files:

```python
@cli.command()
@attach_files()
def download_logo(ctx: typer.Context, manager: FilesManager, url: str):
    response = requests.get(url)
    manager.store_bytes(response.content, "assets/logo.png")
    print("Logo downloaded!")

@cli.command()
@attach_files()
def show_logo(ctx: typer.Context, manager: FilesManager):
    logo_data = manager.load_bytes("assets/logo.png")
    # Display or process logo...
```


### User Data

Store user-specific data:

```python
@cli.command()
@attach_files()
def save_profile(ctx: typer.Context, manager: FilesManager, username: str):
    profile = {
        "username": username,
        "preferences": {
            "theme": "dark",
            "notifications": True
        }
    }
    manager.store_json(profile, f"users/{username}/profile.json")
```


## Security Considerations


### File Permissions

Use the `mode` parameter to set restrictive permissions on sensitive files:

```python
# Owner-only read/write (0o600)
manager.store_json(secrets, "secrets/api_keys.json", mode=0o600)

# Owner read/write, group read (0o640)
manager.store_text(log, "logs/app.log", mode=0o640)
```


### Path Traversal Protection

The `FilesManager` automatically prevents path traversal attacks. Attempts to access files outside the files directory
will raise an error:

```python
# This will raise FilesError
manager.store_text("bad", "../../etc/passwd")

# This will also raise FilesError
manager.store_text("bad", Path("/etc/passwd"))
```


## Differences from Cache

| Feature        | Files                              | Cache                              |
|----------------|------------------------------------|------------------------------------|
| **Purpose**    | Persistent storage                 | Temporary storage                  |
| **Durability** | Data persists indefinitely         | Data may expire or be evicted      |
| **Structure**  | File-based (can inspect manually)  | Database (opaque)                  |
| **Size limits**| No automatic limits                | Configurable size limits           |
| **Eviction**   | Manual deletion only               | Automatic eviction policies        |
| **Use for**    | Config, templates, assets          | Tokens, sessions, API responses    |
