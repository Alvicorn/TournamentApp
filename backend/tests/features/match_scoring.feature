Feature: Match scoring and tie-breaker
  As the source of truth for match outcomes,
  the scoring system must determine winners by cumulative score
  and trigger sudden-death on ties in the final round.

  Background:
    Given a 3-round match between Alice and Bob

  Scenario: Higher cumulative score wins
    Given the round scores are 5-3, 4-4, 3-2
    When the judge ends the final round and submits
    Then Alice is the winner
    And the final score is 12-9

  Scenario: Tied final round triggers sudden-death
    Given the round scores are 3-3, 4-4, 5-5
    When the judge ends the final round
    Then the match enters sudden-death
    And no time limit applies

  Scenario: Forfeit during sudden-death ends the match
    Given the match is in sudden-death
    When Alice forfeits
    Then Bob is the winner
    And the match transitions to pending_review
