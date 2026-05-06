Feature: Late participant addition during round-robin

  Scenario: Participant added to round_robin division gets matches against all existing participants
    Given a division in round_robin state with 3 existing participants and 3 matches
    When admin assigns a 4th participant to the division
    Then 3 new matches are appended to the division
    And the new participant faces each of the 3 existing participants

  Scenario: Participant cannot be added after division advances past round_robin
    Given a division whose state has been manually advanced to play_ins
    When admin attempts to assign a participant
    Then a 409 DIVISION_ADVANCED error is returned
