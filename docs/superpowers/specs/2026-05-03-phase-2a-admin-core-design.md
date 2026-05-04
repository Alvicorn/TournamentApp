# Phase 2a — Admin Core: Data Foundation + CRUD

**Date**: 2026-05-03
**Scope**: All SQLAlchemy models + Alembic migration, tournament/judge/participant/division CRUD (backend + admin UI).
**Demoable result**: Admin can create a tournament, add judges with generated codes, add participants with custom fields, create divisions, and assign competitors to divisions.
**Out of scope (Phase 2b)**: Round-robin generation, match management, activity log writes, activity feed UI, backup job.

---

## 1. Data layer

### 1.1 SQLAlchemy models

All models in `backend/app/models/`, one file per table group. All exported from `app/models/__init__.py` so `alembic/env.py` sees `Base.metadata`.

| File | Tables |
|---|---|
| `tournament.py` | `tournaments` |
| `judge.py` | `judges` |
| `participant.py` | `participants` |
| `division.py` | `divisions` |
| `match.py` | `matches`, `match_rounds`, `score_events` |
| `activity_log.py` | `activity_log` |
| `subscription.py` | `subscriptions`, `broadcasts` |

Every model uses `uuid_pk()`, `TimestampMixin`, and `SoftDeleteMixin` from `app/models/base.py` where applicable (see base.py for the existing helpers).

#### `Tournament`
```python
class LifecycleState(StrEnum):
    SETUP = "setup"
    ACTIVE = "active"
    COMPLETED = "completed"

class Tournament(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tournaments"
    id = uuid_pk()
    name: Mapped[str]
    competition_date: Mapped[date]
    time_zone: Mapped[str]                          # IANA TZ
    rounds_per_match: Mapped[int]
    round_length_seconds: Mapped[int]
    slideshow_slide_seconds: Mapped[int]
    lifecycle_state: Mapped[LifecycleState]         # server_default="setup"
    custom_participant_fields: Mapped[list] = mapped_column(JSONB, server_default="[]")
    is_demo: Mapped[bool] = mapped_column(server_default="false")
    judge_auto_release_seconds: Mapped[int] = mapped_column(server_default="600")
```

Service-layer constraint (not DB): only one `lifecycle_state != completed` AND `deleted_at IS NULL` AND `is_demo = false` tournament at a time.

#### `Judge`
```python
class Judge(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "judges"
    id = uuid_pk()
    tournament_id: Mapped[UUID]                     # FK → tournaments
    name: Mapped[str]
    code: Mapped[str]                               # 8-char, unique within tournament
    current_session_jti: Mapped[UUID | None]        # single-device binding
    is_active: Mapped[bool] = mapped_column(server_default="true")
```
Unique index: `(tournament_id, code) WHERE deleted_at IS NULL`.

#### `Participant`
```python
class Participant(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "participants"
    id = uuid_pk()
    tournament_id: Mapped[UUID]                     # FK → tournaments
    division_id: Mapped[UUID | None]                # FK → divisions, nullable
    name: Mapped[str]
    custom_fields: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    is_withdrawn: Mapped[bool] = mapped_column(server_default="false")
```

#### `Division`
```python
class DivisionState(StrEnum):
    SETUP = "setup"
    ROUND_ROBIN = "round_robin"
    PLAY_INS = "play_ins"
    SEMIS = "semis"
    FINALS = "finals"
    COMPLETED = "completed"
    PAUSED = "paused"

class Division(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "divisions"
    id = uuid_pk()
    tournament_id: Mapped[UUID]                     # FK → tournaments
    name: Mapped[str]
    state: Mapped[DivisionState] = mapped_column(server_default="setup")
    paused_reason: Mapped[str | None]
```

#### `Match`, `MatchRound`, `ScoreEvent`
Defined in `match.py` per the full spec in `docs/engineering/backend.md`. Service layer deferred to Phase 2b — models must exist so the migration is complete.

#### `ActivityLog`
```python
class ActorType(StrEnum):
    ADMIN = "admin"
    JUDGE = "judge"
    SYSTEM = "system"

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = uuid_pk()
    tournament_id: Mapped[UUID]
    division_id: Mapped[UUID | None]
    actor_type: Mapped[ActorType]
    actor_id: Mapped[UUID | None]
    actor_display_name: Mapped[str]
    action: Mapped[str]                             # dot.notation e.g. "match.submitted"
    description: Mapped[str]
    metadata: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

#### `Subscription`, `Broadcast`
Defined per spec. Service layer deferred to Phase 4.

### 1.2 Alembic migration

Single file: `backend/alembic/versions/0002_phase2_core_tables.py`.

Creates all tables and all indexes listed in `docs/engineering/backend.md#key-indexes`, plus:
- `CREATE TYPE lifecycle_state AS ENUM ('setup','active','completed')`
- `CREATE TYPE division_state AS ENUM ('setup','round_robin','play_ins','semis','finals','completed','paused')`
- `CREATE TYPE match_phase AS ENUM ('round_robin','play_in','semi','final','bronze')`
- `CREATE TYPE match_state AS ENUM ('scheduled','in_progress','paused','pending_review','submitted')`
- `CREATE TYPE actor_type AS ENUM ('admin','judge','system')`

`downgrade()` drops all tables and types in reverse order.

### 1.3 SQLAlchemy session

`backend/app/db.py` — add alongside the existing Supabase client:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

`Settings` gains `database_url: str = ""`.

---

## 2. Backend services + routes

### 2.1 Structure

```
backend/app/
  services/
    tournament.py
    judge.py
    participant.py
    division.py
  routes/
    tournaments.py
    judges.py
    participants.py
    divisions.py
```

Routes are thin (parse + validate body, call service, return result). Services own business logic and take a `Session` argument. All admin routes use `AdminUser = Annotated[AdminPrincipal, Depends(require_admin)]`.

### 2.2 Tournament service + routes

**Routes** (`/api/v1/tournaments`):

| Method | Path | Description |
|---|---|---|
| `POST` | `/tournaments` | Create tournament |
| `GET` | `/tournaments/active` | Get current non-demo, non-completed tournament |
| `PATCH` | `/tournaments/{id}` | Edit config |
| `POST` | `/tournaments/{id}/lifecycle` | Transition state |
| `DELETE` | `/tournaments/{id}` | Soft delete (demo or completed only) |

**Service rules**:
- `create`: enforce single-active constraint before insert; capture `time_zone` from request body
- `edit`: reject `custom_participant_fields` mutation when `lifecycle_state != "setup"` → 409 `FIELDS_FROZEN`
- `lifecycle`: valid transitions are `setup→active`, `active→completed`, `active→setup` (forced, warns); on `setup→active` write `custom_participant_fields` as immutable snapshot; on `active→setup` revert to mutable (API returns warning in response body)
- `delete`: reject if `lifecycle_state = "active"` and `is_demo = false` → 409

### 2.3 Judge service + routes

**Routes**:

| Method | Path | Description |
|---|---|---|
| `POST` | `/tournaments/{id}/judges` | Create judge (generates code) |
| `GET` | `/tournaments/{id}/judges` | List active judges |
| `DELETE` | `/judges/{id}` | Soft delete judge |

**Service rules**:
- `create`: call `generate_judge_code()`; retry up to 5 times on unique constraint violation; return generated code in response
- `delete`: set `is_active=False`, `current_session_jti=None`, soft delete; if judge has a match in `in_progress|paused|pending_review` → set match `state="paused"`, clear `assigned_judge_id`; return `{had_active_match: bool, match_id: uuid|null}` so frontend can surface the warning

### 2.4 Participant service + routes

**Routes**:

| Method | Path | Description |
|---|---|---|
| `POST` | `/tournaments/{id}/participants` | Create participant |
| `GET` | `/tournaments/{id}/participants` | List participants |
| `PATCH` | `/participants/{id}` | Edit name / custom fields |
| `DELETE` | `/participants/{id}` | Soft delete or withdraw |

**Service rules**:
- `create` / `edit`: validate `custom_fields` values against tournament's `custom_participant_fields` spec (required fields present, no unknown keys)
- `edit`: blocked when `tournament.lifecycle_state = "completed"` → 409
- `delete`: if participant has no matches → soft delete; if matches exist → `is_withdrawn = True` (historical record kept); return `{action: "deleted"|"withdrawn"}` so frontend shows correct label

### 2.5 Division service + routes

**Routes**:

| Method | Path | Description |
|---|---|---|
| `POST` | `/tournaments/{id}/divisions` | Create division |
| `GET` | `/tournaments/{id}/divisions` | List divisions |
| `PATCH` | `/divisions/{id}` | Rename; pause/resume state (scaffold only — full enforcement in Phase 2b) |
| `DELETE` | `/divisions/{id}` | Soft delete |
| `POST` | `/divisions/{id}/assign-participant` | Assign participant to division |
| `POST` | `/divisions/{id}/move-participant` | Move participant to another division |

**Service rules**:
- `delete`: only when `state = "setup"` and no matches → 409 otherwise
- `assign`: participant must belong to same tournament; participant must not already have a `division_id` → 409 `ALREADY_ASSIGNED`; division must be in `state = "setup"` → 409 `DIVISION_STARTED` (late additions to started divisions handled by Phase 2b's dedicated endpoint)
- `move`: set `participant.division_id = target_division_id`; blocked if either source or target division `state != "setup"` → 409 `DIVISION_STARTED`; participant must have no submitted or in-progress matches in source division

---

## 3. Frontend admin pages

TanStack Query for all data fetching. Mutations call `apiClient.*` helpers and invalidate affected query keys. All admin pages show a "Please use a desktop browser" message on viewports < 1024px.

### 3.1 `AdminHome`

- **No tournament**: "Get started by creating your first tournament." + CTA button → `/admin/setup`
- **Tournament exists**: status card (name, date, lifecycle badge, demo badge if `is_demo`), counts (judges, participants, divisions), nav links
- Activity feed pane: stub ("Activity feed — coming in Phase 2b")

### 3.2 `AdminSetup`

Tournament create/edit form:
- Name, competition date, rounds per match, round length (seconds), slideshow slide seconds, judge auto-release seconds
- Time zone: pre-populated from `Intl.DateTimeFormat().resolvedOptions().timeZone`, editable dropdown of IANA zones (or free text with validation)
- `is_demo` toggle
- **Custom fields builder**: ordered list of field rows, each with key (slug), label, type (text/number/select), required toggle; add/remove/reorder rows; editing disabled when `lifecycle_state != "setup"` with a lock icon and "Fields are frozen — transition back to Setup to edit"
- **Lifecycle controls**: "Activate Tournament" button (with confirmation modal: "Custom fields will be frozen. Participants must have all required fields filled."); "Mark Completed" button; "Force back to Setup" button (hard warning modal)

### 3.3 `AdminJudges`

Table: name, code displayed as `XXXX-XXXX` format, active badge.
"Add Judge" button → inline row form (name only).
After creation: code displayed in a dismissable copy-badge ("ABCD-EFG1 — copied!").
Delete button → confirmation modal; if `had_active_match` in response, modal text includes "This judge has an active match (Match #N). Removing them will pause that match."

### 3.4 `AdminParticipants`

Table: name, division (linked chip), custom field columns (rendered from tournament spec), status badge (active/withdrawn/deleted).
"Add Participant" → slide-over or modal form with name + custom fields.
Inline edit for name/custom fields (pencil icon → editable row).
Delete → confirm; label button "Withdraw" if participant has matches, "Delete" if not.

### 3.5 `AdminDivisions`

Cards or table: division name, state badge, participant count.
"Add Division" inline input.
Click → `AdminDivisionDetail`.

### 3.6 `AdminDivisionDetail`

Two-column layout:
- **Left**: participants assigned to this division (name, custom field summary, remove/move button)
- **Right**: unassigned participants pool (filtered to same tournament, no division yet); "Assign" button per row

Move participant: dropdown of other divisions in the same tournament.
Division rename: inline edit on the heading.
"Generate Round Robin" button: disabled with tooltip "Assign participants first, then generate matches" (Phase 2b wires the actual call).

### 3.7 API client additions

Extend `frontend/src/api/client.ts` with typed fetch helpers for every new endpoint. `useTournamentStore` hydrates on admin login by calling `GET /tournaments/active`.

---

## 4. Testing

### 4.1 Test infrastructure changes

`backend/tests/conftest.py` — add:
- Testcontainers Postgres fixture (function-scoped): spins up ephemeral Postgres, runs Alembic migrations, yields `Session`
- `db_session` fixture injected into service tests
- Keep existing `TestClient` fixture for route tests; update it to use the Testcontainers DB

`backend/tests/fixtures/tournaments.py` — factory helpers: `make_tournament()`, `make_judge()`, `make_participant()`, `make_division()`.

### 4.2 Unit tests

`tests/test_tournament_service.py`:
- Valid lifecycle transitions pass; invalid ones raise `HTTPException(409)`
- `custom_participant_fields` edit rejected when `lifecycle_state = "active"`
- Single-active constraint: second non-demo non-completed tournament rejected

`tests/test_participant_service.py`:
- Required custom field missing → validation error
- Unknown custom field key → validation error
- Delete with no matches → soft delete; with matches → `is_withdrawn`

`tests/test_division_service.py`:
- Assign participant already in a division → 409 `ALREADY_ASSIGNED`
- Move participant after division started → 409 `DIVISION_STARTED`
- Delete division with matches → 409

### 4.3 BDD feature files

`tests/features/tournament_lifecycle.feature`:
```gherkin
Feature: Tournament lifecycle transitions
  Scenario: Setup to active freezes custom fields
  Scenario: Cannot edit custom fields when active
  Scenario: Force back to setup re-enables custom field editing
  Scenario: Cannot activate a second non-demo tournament
  Scenario: Invalid transition rejected (completed → active)
```

`tests/features/custom_field_freezing.feature`:
```gherkin
Feature: Custom participant field spec management
  Scenario: Adding a field in setup back-fills null on existing participants
  Scenario: Removing a field in setup drops values from existing participants
  Scenario: Field spec is immutable when tournament is active
  Scenario: Reverting to setup restores mutability with warning
```

### 4.4 Integration tests

`tests/integration/test_admin_flow.py`:
- Full happy path: create tournament → add 3 judges → add 6 participants → create 2 divisions → assign 3 participants each
- Custom field freeze: POST to `/tournaments/{id}` to edit fields when active returns 409
- Single-active constraint enforced at API level
- Judge delete with active match: match paused, assignment cleared, `had_active_match=true` in response
- Participant withdraw vs delete depending on match existence
- Move participant between divisions

### 4.5 Frontend tests

`frontend/src/test/AdminSetup.test.tsx`:
- Custom field builder: add row, remove row, reorder rows
- Time zone auto-populated on mount
- Freeze warning modal shown on lifecycle transition

`frontend/src/test/AdminJudges.test.tsx`:
- Code displayed in `XXXX-XXXX` dash format
- Delete confirmation modal shows active-match warning when applicable

---

## 5. Commit strategy

Each commit is independently buildable and passes CI:

1. **`feat(models): add all SQLAlchemy models + migration 0002`** — all models, migration, `get_db()` session factory, `database_url` setting. No routes yet.
2. **`feat(api): tournament CRUD + lifecycle routes`** — tournament service + routes + unit tests + BDD lifecycle feature
3. **`feat(api): judge CRUD routes`** — judge service + routes + tests
4. **`feat(api): participant CRUD routes`** — participant service + routes + custom field validation + tests + BDD custom_field_freezing feature
5. **`feat(api): division CRUD + participant assignment routes`** — division service + routes + integration test
6. **`feat(frontend): AdminHome + AdminSetup pages`** — tournament status + create/edit form
7. **`feat(frontend): AdminJudges page`**
8. **`feat(frontend): AdminParticipants page`**
9. **`feat(frontend): AdminDivisions + AdminDivisionDetail pages`**
10. **`test(integration): full admin happy-path flow`** — cross-cutting integration test covering the full 2a journey

Phase 2b begins after all 10 commits are merged.
