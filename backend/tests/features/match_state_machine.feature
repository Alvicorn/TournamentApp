Feature: Match state machine — result editing rules

  Scenario: Edit result allowed on submitted match in round_robin division
    Given a submitted match in a round_robin division
    When admin edits the result with new scores
    Then the match result is updated
    And an activity log entry with action match.result_edited exists

  Scenario: Edit result blocked when division is not round_robin
    Given a submitted match in a division with state play_ins
    When admin attempts to edit the result
    Then a 409 error is returned

  Scenario: Edit result blocked on a non-submitted match
    Given a scheduled match in a round_robin division
    When admin attempts to edit the result
    Then a 409 error is returned
