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

  Scenario: Adding a custom field does not break existing participants
    Given a tournament in setup state with an existing participant having no extra fields
    When admin PATCHes custom_participant_fields to add a belt field
    Then the response status is 200
    And the existing participant can still be retrieved successfully

  Scenario: Removing a custom field updates the tournament spec
    Given a tournament in setup state with a participant having a belt field value
    When admin PATCHes custom_participant_fields to remove all fields
    Then the response status is 200
    And the tournament custom_participant_fields is empty
