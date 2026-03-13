Feature: Cache management via CLI
  As a developer using typerdrive
  I want to manage the application cache through a CLI
  So that I can inspect and clear cached data

  Background:
    Given a CLI app with cache subcommand

  Scenario: Show displays all cache entries
    Given the cache contains key "jawa" with value "Utinni!"
    And the cache contains key "ewok" with value "Yub Nub!"
    When I run the cache show command
    Then the command succeeds
    And the output contains "Cache contains 2 entries"
    And the output contains "jawa"
    And the output contains "ewok"

  Scenario: Show with stats flag displays cache statistics
    Given the cache contains key "key1" with value "value1"
    And the cache contains key "key2" with value "value2"
    When I run the cache show command with "--stats"
    Then the command succeeds
    And the output contains "Cache Statistics"
    And the output contains "Hits"
    And the output contains "Misses"

  Scenario: Clear removes all entries after confirmation
    Given the cache contains key "jawa" with value "Utinni!"
    And the cache contains key "hutt" with value "Boska!"
    When I run the cache clear command and confirm with "y"
    Then the command succeeds
    And the output contains "Cleared 2 entries from cache"
    And the cache is empty

  Scenario: Clear is cancelled when confirmation is denied
    Given the cache contains key "jawa" with value "Utinni!"
    And the cache contains key "hutt" with value "Boska!"
    When I run the cache clear command and confirm with "n"
    Then the command fails with exit code 1
    And the cache still contains key "jawa"

  Scenario: Clear removes only entries with a specific group
    Given the cache contains key "rebel1" with value "Luke" in group "rebels"
    And the cache contains key "rebel2" with value "Leia" in group "rebels"
    And the cache contains key "sith1" with value "Vader" in group "empire"
    When I run the cache clear command with "--group=rebels" and confirm with "y"
    Then the command succeeds
    And the output contains "Cleared 2 entries with group 'rebels'"
    And the cache still contains key "sith1"
    And the cache does not contain key "rebel1"
