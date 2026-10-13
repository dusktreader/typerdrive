Feature: SQLite database via CLI
  As a developer using typerdrive
  I want commands to share an application database
  So that my application can persist structured data safely

  Background:
    Given a CLI app with database commands and migrations

  Scenario: Fresh attachment creates and migrates the database before the callback
    When an async command inserts "first row"
    Then the command succeeds
    And the output proves attachment initialization completed
    And the migration ledger contains 1 record

  Scenario: Async commands persist rows across invocations
    When an async command inserts "first row"
    And an async command reads the stored rows
    Then the command succeeds
    And the output contains "first row"
    And the migration ledger contains 1 record

  Scenario: Sync wrappers persist rows across invocations
    When a sync command inserts "sync row"
    And a sync command reads the stored rows
    Then the command succeeds
    And the output contains "sync row"

  Scenario: Migrations run before callback and failures suppress the callback
    Given a database with a migration checksum mismatch
    When I invoke an attached command
    Then the command fails
    And the application callback was not entered

  Scenario: Empty migration descriptions suppress callbacks
    Given a migration with an empty description
    When I invoke an attached command
    Then the command fails
    And the application callback was not entered

  Scenario: Empty migration SQL suppresses callbacks
    Given a migration with empty SQL
    When I invoke an attached command
    Then the command fails
    And the application callback was not entered

  Scenario: Failed SQL migration rolls back and can be retried in registration order
    Given a migration sequence with a failing second migration
    When I set up and migrate with failing SQL
    Then the command fails
    And only the first migration is recorded
    When I correct the second migration and migrate
    Then the command succeeds
    And migration ledger IDs match registration order

  Scenario: Database path inspect and status do not create an absent database
    When I run database path inspect and status
    Then all database commands succeed
    And the output reports the migration as pending
    And the database file remains absent

  Scenario: Setup creates an empty database and migrate applies pending schema
    When I run migrate against the absent database
    Then migrate fails without creating the database
    When I set up the database twice
    Then setup succeeds and leaves application migrations pending
    And the database has no application schema
    When I inspect, migrate, and check status
    Then migrations are applied and inspect reports WAL metadata

  Scenario: Reset rebuilds the current registered schema
    Given the database contains an application row
    When I reset the database and confirm
    Then the reset database contains the current schema and no old row

  Scenario: Declining reset preserves application data and migration history
    Given the database contains an application row
    When I decline database reset
    Then the command fails
    And the existing application row and migration history remain

  Scenario: Concurrent processes apply each migration exactly once
    When two processes migrate the database at the same time
    Then both migration processes succeed
    And the migration ledger and schema contain one application

  Scenario: Invoking an attached command from a running event loop fails clearly
    When I invoke an attached command from an active event loop
    Then the command fails
    And the output explains the event loop limitation
    And the database file remains absent

  Scenario: Async command failure closes the database manager
    When an async command raises an error
    Then the command fails
    And failure handling closes the database manager

  Scenario: Cancellation closes the database manager
    When an async command cancels itself
    Then cancellation closes the manager before it escapes
