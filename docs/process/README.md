# Process

Meta-concerns: how we test, what's pending, why decisions were made.

## Files

- **[`testing.md`](testing.md)** — Test layers (unit / BDD / integration / E2E / simulation / load), tooling, CI pipeline.
- **[`backlog.md`](backlog.md)** — Phased implementation plan, future work, known limitations.
- **[`memory.md`](memory.md)** — Append-only log of decisions and gotchas. Read last; refer often.

## When to update files here

- New test added → maybe update `testing.md` if it's a new pattern
- Task completed → check it off in `backlog.md`
- New phase added → `backlog.md`
- Decision made → log it in `memory.md`
- Gotcha discovered → log it in `memory.md`

`memory.md` is **append-only**. Don't rewrite history; add a new dated entry.
