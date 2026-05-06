Feature: Custom participant field spec freezing

  Scenario: Custom fields locked while tournament is active
    Given an active tournament with custom fields
    When admin PATCHes custom_participant_fields
    Then the response status is 409
    And the error detail contains "CUSTOM_FIELDS_FROZEN"

  Scenario: Custom fields editable during setup
    Given a tournament in setup state
    When admin PATCHes custom_participant_fields with a new field
    Then the response status is 200
    And the returned custom_participant_fields contains the new field
