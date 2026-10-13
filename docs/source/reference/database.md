# typerdrive database modules

Database attachment creates and configures an absent database, then applies registered migrations before command code
runs. `db setup` creates an empty database without application migrations. `db migrate` requires an existing database
and
applies pending migrations without creating an absent file. See the [database feature guide](../features/database.md)
for lifecycle and command details.


::: typerdrive.database
::: typerdrive.database.attach
::: typerdrive.database.commands
::: typerdrive.database.exceptions
::: typerdrive.database.manager
::: typerdrive.database.migrations
