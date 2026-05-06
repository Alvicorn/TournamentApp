Feature: Round-robin match generation
  The round-robin generator must pair every participant against every other
  participant exactly once, with no bye matches recorded.

  Scenario: Even number of participants
    Given 4 participants
    When round-robin matches are generated
    Then there are 6 matches
    And every pair plays exactly once

  Scenario: Odd number of participants — no byes recorded
    Given 5 participants
    When round-robin matches are generated
    Then there are 10 matches
    And every pair plays exactly once

  Scenario: Minimum of 2 participants
    Given 2 participants
    When round-robin matches are generated
    Then there is 1 match

  Scenario: Fewer than 2 participants returns empty
    Given 1 participant
    When round-robin matches are generated
    Then there are 0 matches

  Scenario: Same input always produces the same output
    Given 6 participants
    When round-robin matches are generated twice with the same input
    Then both results are identical
