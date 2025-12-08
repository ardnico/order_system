# Household settings polish, language defaults, and onboarding clarity

This ExecPlan is a living document and must be maintained in accordance with `.agent/PLANS.md` from the repository root. Update every section as progress is made.

## Purpose / Big Picture

Household members should be able to sign up smoothly, land on a clear how-to page, and configure household-wide preferences (language, theme, font, and related defaults) without confusion. After implementation, a new user can join an existing household with the correct join code, read a concise usage guide from the navigation, adjust household settings in one place, and see the interface default to Japanese unless a different language is explicitly chosen.

## Progress

- [x] (2025-12-08 10:50Z) Document current state and risks; confirm existing routes/templates for registration, settings, and language handling.
- [x] (2025-12-08 10:53Z) Implement help/usage page with navigation entry and localized strings.
- [x] (2025-12-08 10:53Z) Fix household join flow to accept valid join codes when creating a new account for an existing household; add tests/validation where feasible.
- [x] (2025-12-08 10:53Z) Expand household settings to cover core preferences (language/theme/font defaults, household name/join code visibility or regeneration) and ensure forms persist values.
- [x] (2025-12-08 10:53Z) Audit language handling for consistency (session vs. household defaults, template coverage) with Japanese as default; adjust strings and persistence logic.
- [x] (2025-12-08 10:55Z) Run tests/manual checks and update retrospective.

## Surprises & Discoveries

- Observation: Registration joined-household flow was failing because two `join_code` inputs existed in the form, and the hidden/new-field value shadowed the real code submitted for existing households.
  Evidence: `app/templates/register.html` used the same `name` for both inputs; backend comparison in `register` treated the blank value as authoritative and rejected valid codes.

## Decision Log

- Decision: Extend the existing `/settings/language` handler to manage household metadata (name/join code) and appearance defaults to keep compatibility with tests and UI wiring.
  Rationale: Reusing the established route avoids breaking existing form posts and keeps theme/font updates in one place while adding household-level controls and flash messaging.
  Date/Author: 2025-12-08 / assistant

## Outcomes & Retrospective

- Added a public help page, navigation entry, and localized guidance so onboarding steps are visible in both Japanese and English.
- Fixed household registration to honor the provided join code for existing households by separating form fields and backend handling.
- Settings now manage household name, join code regeneration, and appearance defaults with session updates and localized flash messaging; language/theme/font fall back safely to Japanese defaults when invalid.
- All automated tests pass after the changes.

## Context and Orientation

The app is a FastAPI project under `app/` with Jinja2 templates in `app/templates/` and static assets in `app/static/`. Session-based auth and household context live in `app/auth.py` and `app/main.py` (registration, task views, settings). Language/theme/font preferences are stored on the `Household` model (`app/models.py`) and copied into the session via `get_language`, `get_theme`, and `get_font` (all in `app/main.py`). UI strings are defined in the `UI_STRINGS` dict within `app/main.py`. Settings UI is rendered from `app/templates/settings.html`, and registration/login forms are in `app/templates/register.html` and `app/templates/login.html`.

Known issues to address:
- Registering to an existing household reports "Invalid join code" even when the code matches; investigate duplicate `join_code` inputs in `register.html` and backend validation in `app/main.py` register handler.
- No dedicated how-to/usage page linked from the navigation.
- Household settings page lacks visibility/control for household metadata (e.g., name/join code) and needs reliable persistence of language/theme/font defaults.
- Language defaults should favor Japanese, with consistent session/household propagation and localized strings for new UI.

## Plan of Work

Describe edits in order, naming files and functions precisely:
1) Registration flow: Inspect `app/main.py` register handler and `app/templates/register.html` to ensure the join-code submitted when joining existing households is the intended value (unique form names or backend selection logic). Add server-side validation/tests for join-code matching.
2) Usage/help page: Add a new template under `app/templates/` with clear onboarding steps (signup, joining via join code, task/reward basics, language settings). Create a route in `app/main.py` (e.g., `/help`), add navigation entry in `app/templates/base.html`, and localize strings in `UI_STRINGS`.
3) Household settings: Expand `app/templates/settings.html` and related POST endpoints in `app/main.py` to allow viewing/updating household name and join code (including regeneration) alongside language/theme/font defaults. Ensure values persist to `Household` and session, with validation for allowed options.
4) Language consistency: Review `get_language`, `build_context`, and templates to enforce Japanese as default, ensure new UI strings exist for both languages, and keep session overrides aligned with household defaults (e.g., on login/register and settings updates). Consider resetting session language when household default changes.
5) Testing/verification: Add targeted tests (if feasible in `tests/`) for registration join-code validation and settings updates, or document manual steps. Run `pytest` and, if needed, run the FastAPI app locally to verify pages render with correct language/theme defaults.

## Concrete Steps

- Working directory: repository root `/workspace/order_system`.
- Commands to run during implementation and verification:
  - `python -m pytest` — run automated tests (if present) after changes.
  - `uvicorn app.main:app --reload` — manual verification server; visit `/register`, `/settings`, `/help` as needed.
- File edits anticipated:
  - `app/main.py` — routes, language/session logic, settings handlers, UI strings.
  - `app/templates/base.html` — navigation update.
  - `app/templates/register.html` — form field fixes for join code.
  - `app/templates/settings.html` — household metadata controls and language/theme/font persistence.
  - New `app/templates/help.html` (or similar) — usage guide.
  - Possible additions under `tests/` for regression coverage.

## Validation and Acceptance

- Registering to an existing household with the correct join code succeeds without "Invalid join code" errors; incorrect codes still reject with an error flash.
- Navigation includes a clear help/usage link; `/help` displays bilingual content with default Japanese when session is new.
- Settings page allows viewing/updating household name, join code (including regenerating or copying), language, theme, and font; changes persist and apply to subsequent requests.
- Language handling: fresh sessions default to Japanese, household language updates propagate to session, and new UI strings appear in both locales. Manual toggling via settings reflects immediately in UI text.
- Automated tests (if added) pass; manual smoke test confirms pages render and forms submit without server errors.

## Idempotence and Recovery

- Form submissions are additive/overwrite-safe: rerunning updates replaces existing values without duplicates. Join-code regeneration uses random tokens without relying on prior state; rollback by re-entering the previous code if needed. Session language/theme/font updates can be retried by reloading settings. Database changes are limited to the active household records.

## Artifacts and Notes

- Capture any relevant terminal output (test runs, manual curl responses) inside this section when updating the plan.

## Interfaces and Dependencies

- Key interfaces: FastAPI routes in `app/main.py` (`/register`, `/help`, `/settings/*`), templates under `app/templates/`, and SQLModel models in `app/models.py` (`Household`, `User`). Ensure imports remain unchanged (avoid wrapping imports in try/except). Use existing helpers `build_context`, `get_language`, `get_theme`, and `get_font` for consistency. Joining households depends on the `Household.join_code` string; validation should be case-insensitive and trimmed.
