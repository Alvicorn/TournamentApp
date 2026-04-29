# User Stories

These are the original requirements as captured at project start. Treat as the canonical scope of MVP. Refinements that emerged during design are documented in [`rules.md`](rules.md), [`backend.md`](../engineering/backend.md), and [`frontend.md`](../engineering/frontend.md).

## Admin

- Initialize a new tournament by configuring parameters: tournament name, competition date, number of rounds per match, length of each round, slideshow slide duration, custom participant fields.
- Manually register a judge by name; system generates a unique code tied to that judge for login.
- Manually remove a judge by name and revoke their privileges.
- Manually add a participant by name and any custom fields defined at tournament initialization.
- Manually edit participant details to correct registration mistakes.
- Manually remove a participant so withdrawn competitors don't appear in matches.
- See all participant attributes to verify division eligibility.
- Create divisions to group competitors appropriately.
- Move a participant if they're placed in the wrong division.
- Have the system automatically generate round-robin matches so every competitor faces every other competitor.
- See all matches in a division to review the schedule.
- Manually modify matches and change the order of matches.
- Pause/resume a division in case of a prolonged issue.
- Edit match results after they've taken place in case of mistakes.
- Broadcast information to everyone subscribed.
- *(Added)* Forcibly reassign a stuck match to a different judge.
- *(Added)* Run a tournament in dry-run / demo mode for pre-event practice.
- *(Added)* View a real-time activity feed showing actions across all parallel divisions.
- *(Added)* Add late participants during round-robin (matches appended, played history preserved).
- *(Added)* Send broadcasts targeted at subscribers and/or public dashboard banner.
- *(Added)* Preview as Public or Judge to verify what users see during a live tournament.
- *(Added)* See an alert when matches are unclaimed and judges may be needed.
- *(Added)* View a snapshot list (read-only) showing automatic backups taken before risky operations.

## Judge

- Log in with their custom judge code.
- View all active divisions and the matches in each division.
- Assign self to a match within a division. Can only judge one match at a time.
- Reorder upcoming matches in a division.
- Start a match that hasn't begun.
- Start/pause the time for each round throughout the match.
- Mark a competitor as forfeit to terminate a match immediately, with review before submitting.
- Increment/decrement points as the match progresses.
- Review results before declaring a winner and submitting.
- *(Added)* Undo the last few score events to recover from misclicks.
- *(Added)* Release a claimed match before starting it (in case of misclick).

## Public

- View a main dashboard with a slideshow of division-specific information. Each slide shows: current standings, current match, live score, next match-up. Gold and bronze medal matches display a special icon. Each slide stays active for a duration set by admin.
- View a specific division and see current standings, current match, live score, next match-up.
- View a competitor's progress and competition record for the tournament.
- Subscribe to a specific competitor to receive notifications (match start, broadcast info).
- Easily unsubscribe from a competitor.
- Subscribe/unsubscribe to multiple competitors.
- *(Added)* Print-friendly bracket / standings view for paper backup.
- *(Added)* See a clear "connection lost" indicator if live data stops flowing.
- *(Added)* See queue position ("#3 in queue") for upcoming matches.
- *(Added)* View tournament results indefinitely after a tournament completes.
