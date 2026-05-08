Feature: Tournament lifecycle transitions

  Scenario: Activating a tournament freezes custom fields
    Given a tournament in setup state with custom fields defined
    When the admin transitions the tournament to active
    Then the lifecycle state is active
    And modifying custom_participant_fields returns 409

  Scenario: Demo tournament can be reset
    Given a demo tournament in active state with a judge
    When the admin resets the tournament
    Then the lifecycle state is setup
    And the judge is soft-deleted

  Scenario: Non-demo tournament cannot be reset
    Given a non-demo tournament in active state
    When the admin attempts to reset the tournament
    Then a 409 error is returned with detail containing "demo"

  Scenario: Completing a tournament blocks participant updates
    Given a tournament in active state with a participant
    When the admin completes the tournament
    And admin attempts to update the participant
    Then a 409 error is returned with TOURNAMENT_COMPLETED detail
