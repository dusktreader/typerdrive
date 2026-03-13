Feature: File storage management via CLI
  As a developer using typerdrive
  I want to store and retrieve files through the CLI app
  So that my app can persist arbitrary data across invocations

  Background:
    Given a CLI app with files subcommand

  Scenario: Store text file via attach_files decorator
    When a command stores text "Hello from Tatooine!" at path "message.txt"
    Then the command succeeds
    And the file "message.txt" exists in the files directory
    And the file "message.txt" contains text "Hello from Tatooine!"

  Scenario: Store JSON data via attach_files decorator
    When a command stores JSON with planet "Tatooine" and moons 2 at path "data.json"
    Then the command succeeds
    And the file "data.json" exists in the files directory
    And the file "data.json" contains JSON with key "planet" equal to "Tatooine"

  Scenario: Store binary data via attach_files decorator
    When a command stores bytes at path "image.bin"
    Then the command succeeds
    And the file "image.bin" exists in the files directory

  Scenario: Load text file via attach_files decorator
    Given the file "message.txt" contains pre-stored text "Force be with you"
    When a command loads and prints text from "message.txt"
    Then the command succeeds
    And the output contains "Force be with you"

  Scenario: Load JSON data via attach_files decorator
    Given the file "config.json" contains pre-stored JSON with key "level" equal to "debug"
    When a command loads and prints JSON from "config.json"
    Then the command succeeds
    And the output contains "debug"

  Scenario: Files show command displays stored files
    Given the file "quotes/yoda.txt" contains pre-stored text "Do or do not"
    When I run the files show command
    Then the command succeeds
    And the output contains "yoda.txt"

  Scenario: Files manager is accessible via context
    When a command accesses the files manager through the typer context
    Then the command succeeds
    And the output contains "manager retrieved"
