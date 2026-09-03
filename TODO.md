- Set METAVAR in typer-repyt for nested models correctly
- Show start and end of command if logging is attached?
- consider an `unpack_path` parameter for `_x` methods that serialize the response by extracting a JMESPath from the
  response
- Add a database feature: `@attach_database()` manages a SQLite connection whose path follows the XDG convention
  (`~/.local/state/<app_name>/db.sqlite`), handles connection lifecycle (creation, teardown, context manager), and
  injects a `DatabaseManager` onto `ctx.obj`. No ORM — schema and querying are the app's responsibility. Apps that
  want an ORM can layer SQLModel or SQLAlchemy on top of the connection typerdrive provides. Optionally add a `db`
  management subcommand (inspect, reset, path).
