Feature: HTTP client attachment via CLI
  As a developer using typerdrive
  I want to attach HTTP clients to my CLI commands
  So that my app can make API calls with a configured base URL

  Background:
    Given a CLI app with a mock HTTP server

  Scenario: Attach client with explicit base URL
    When a command attaches a client named "jedi" with base URL "https://the.force.io"
    Then the command succeeds
    And the client "jedi" has base URL "https://the.force.io"

  Scenario: Attach client with base URL from settings
    Given settings with base_url "https://the.force.io"
    When a command attaches a client named "jedi" using settings key "base_url"
    Then the command succeeds
    And the client "jedi" has base URL "https://the.force.io"

  Scenario: Attach multiple clients
    When a command attaches clients "jedi" at "https://the.force.io" and "sith" at "https://the.dark.side"
    Then the command succeeds
    And the client "jedi" has base URL "https://the.force.io"
    And the client "sith" has base URL "https://the.dark.side"

  Scenario: Client is accessible as a command parameter
    When a command receives the client "jedi" at "https://the.force.io" as a parameter
    Then the command succeeds
    And the output contains "client ready"

  Scenario: Attach client fails with invalid URL
    When a command tries to attach a client with an invalid URL "not-a-url"
    Then the command fails with exit code 1
    And the output contains "Couldn't use"

  Scenario: Client makes a successful GET request
    Given a mock server at "https://swapi.test" returning {"name": "Luke Skywalker"}
    When a command uses the client to GET "/person"
    Then the command succeeds
    And the output contains "Luke Skywalker"
