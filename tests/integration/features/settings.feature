Feature: Settings management via CLI
  As a developer using typerdrive
  I want to manage application settings through a CLI
  So that my app's configuration persists across invocations

  Background:
    Given a CLI app with settings subcommand

  Scenario: Bind saves all required fields to disk
    When I run the settings bind command with "--name=jawa" and "--planet=tatooine"
    Then the command succeeds
    And the settings file contains name "jawa" and planet "tatooine"
    And the output contains "saved to"

  Scenario: Bind fails when required fields are missing
    When I run the settings bind command with "--name=jawa" only
    Then the command fails with exit code 2
    And the output contains "Missing option"

  Scenario: Update saves partial fields without failing on missing required fields
    When I run the settings update command with "--name=hutt"
    Then the command succeeds
    And the settings file contains name "hutt"
    And the output contains "Invalid Values"

  Scenario: Unset resets a field to its default value
    Given the settings file has name "pyke", planet "oba diah", is_humanoid true, alignment "evil"
    When I run the settings unset command with "--alignment"
    Then the command succeeds
    And the settings file has alignment "neutral"

  Scenario: Unset can leave settings in an invalid state
    Given the settings file has name "pyke", planet "oba diah", is_humanoid true, alignment "evil"
    When I run the settings unset command with "--name" and "--planet"
    Then the command succeeds
    And the output contains "Invalid Values"

  Scenario: Show displays current settings values
    Given the settings file has name "jawa", planet "tatooine", is_humanoid true, alignment "neutral"
    When I run the settings show command
    Then the command succeeds
    And the output contains "jawa"
    And the output contains "tatooine"

  Scenario: Reset clears all settings back to defaults after confirmation
    Given the settings file has name "hutt", planet "nal hutta", is_humanoid false, alignment "evil"
    When I run the settings reset command and confirm with "y"
    Then the command succeeds
    And the output contains "Invalid Values"
    And the settings file does not contain name "hutt"

  Scenario: Reset is cancelled when confirmation is denied
    Given the settings file has name "hutt", planet "nal hutta", is_humanoid false, alignment "evil"
    When I run the settings reset command and confirm with "n"
    Then the command fails with exit code 1
    And the settings file still contains name "hutt"
