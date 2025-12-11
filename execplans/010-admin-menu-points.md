# Admin console, menu media, and contribution rewards

This ExecPlan must be maintained per `.agent/PLANS.md`. It is a living, self-contained guide enabling a novice to deliver an admin console with root access, richer menu creation (images, more ingredients, unit autofill), and contribution-based point rewards.

## Purpose / Big Picture

After this change, admins can oversee every household and user from a dedicated admin-only UI using a root account. Menu creation becomes richer: users can add more than five ingredients, attach an image, and have units auto-filled based on selected ingredients. Contribution actions like adding or editing menus and meal plans will award configurable points so helpful activity is recognized. Users should experience a smoother menu form and admins gain centralized control.

## Progress

- [x] (2025-01-09 00:00Z) Draft ExecPlan with scope, context, and steps.
- [x] (2025-01-09 01:00Z) Implemented model updates (menu image_url, household contribution_rate, user contribution_credit) and root seeding.
- [x] (2025-01-09 01:20Z) Built menu form changes with dynamic rows, unit autofill, and image uploads wired through persistence.
- [x] (2025-01-09 01:35Z) Added contribution reward logic for menu/meal plan edits with configurable rate surfaced in settings.
- [x] (2025-01-09 01:45Z) Created admin-only routes/templates for household/user CRUD with gating and root access.
- [x] (2025-01-09 01:55Z) Added tests for admin login and contribution awards plus adjusted fixtures for new upload requirements.
- [x] (2025-01-09 02:05Z) Ran full test suite and verified menu ingredients, imports, and meal-plan tasks.

## Surprises & Discoveries

- Form routes that mix UploadFile and Form require multipart posts; tests needed explicit empty `files={}` payloads to avoid 422s.

## Decision Log

- Decision: Use a dedicated root admin account to manage all households; keep household_id nullable for root while preserving existing household scoping elsewhere via guards.
  Rationale: Root needs cross-household access; current model enforces household_id, so we will relax it for admin-only cases while keeping member flows scoped to a household.
  Date/Author: 2025-01-09 / Coding Agent

## Outcomes & Retrospective

- The import flow now correctly restores menus and ingredients after addressing a missing query in the importer.
- Normalizing list-like form fields (especially when multipart data is coerced into stringified lists) was essential to keep ingredient quantities and meal-plan selections intact.
- Meal plan task generation required explicit household scoping in tests to avoid clashing with the seeded root admin.

## Context and Orientation

The FastAPI app lives in `app/main.py` with SQLModel models in `app/models.py`. Templates are under `app/templates/`, styles in `app/static/style.css`. Menu creation uses `/menus` routes with forms in `app/templates/menus/list.html` and `app/templates/menus/edit.html`; ingredients persist via `save_menu_ingredients` in `app/main.py`. Uploaded instruction images are stored under `app/static/uploads` using `store_instruction_upload`; a similar mechanism can save menu images. Users have `is_admin` flag, but no global admin UI exists. Point tracking uses `PointTransaction` records when tasks are approved; we must extend earning to menu/meal-plan contributions with configurable rate, likely stored per household and editable in settings.

## Plan of Work

1. Extend data models: add optional `image_url` to `Menu`; allow `User.household_id` to be nullable to support a root admin; add household setting (e.g., `contribution_rate`) controlling how many edits per point and track contribution events via `PointTransaction` with a standard description.
2. Migration/data handling: ensure seeding creates a root admin account with secure default password from env or config; adjust auth to allow root login without household; gate household-specific pages to require household_id unless admin explicitly selecting a household context.
3. Menu UX: Update templates to allow dynamic ingredient rows (add/remove beyond five), include file input for menu image, and auto-fill unit select when an ingredient with stored `unit` is chosen (progressively enhance with JS). Backend must accept more ingredients and persist image uploads alongside the menu record.
4. Admin UI: Add routes under `/admin` guarded by `is_admin` and household_id is None or flag; list households/users, create/edit/delete households and users, and assign admin flag. Include forms and templates under `app/templates/admin/` plus navigation links visible only to admins.
5. Contribution points: define helper to award points for menu creation/edit and meal plan creation/edit; use configurable rate stored on household (default 10 actions per point). Update settings page to edit the rate. Ensure points ledger view reflects new transactions.
6. Tests: add coverage for unit autofill, menu image upload persistence, admin access control, root login, household/user CRUD via admin, contribution rate application, and export/import including new menu fields and settings. Adjust fixtures as needed.

## Concrete Steps

1. Modify `app/models.py` to add `image_url` to `Menu` and optional `contribution_rate` to `Household` (default 10). Make `User.household_id` nullable for root and reflect relationships safely. Update any type hints relying on non-null household_id.
2. Update database initialization/seed in `app/main.py` to create a root admin (email `root@local` or from env, password from env/`ROOT_PASSWORD`, is_admin True, household_id None). Ensure login logic allows household-less admin and bypasses household join validation. Adjust `require_user` and guards so non-admin users still need household contexts.
3. Enhance menu endpoints: accept `image_file` UploadFile, save via new helper similar to `store_instruction_upload`; store URL on menu. Adjust `save_menu_ingredients` to accept more rows (do not cap at five) and unit lookup to respect ingredient default unit when client sends empty unit. Update templates (`menus/list.html`, `menus/edit.html`) with JS to add rows dynamically, auto-fill unit select on ingredient input using a JSON data attribute, and include image preview/upload field.
4. Create admin blueprint: add `/admin` index with household/user lists; CRUD endpoints for households (name, join_code, language/theme/font/contribution_rate) and users (email, display name, password reset, admin flag, household assignment). Restrict visibility via dependency enforcing `user.is_admin` and optionally `user.household_id is None` for root-only screens. Add templates and navigation (conditional link in `base.html`).
5. Implement contribution point awarding: introduce helper to log `PointTransaction` with description when menus or meal plans are created/updated. Use household `contribution_rate` to convert actions to points (e.g., every N actions award 1 point, fractional accumulation tracked via counter stored per household or user—consider per-user pending counter field or session). A simple approach: track cumulative contributions per user via new table or counter in session; if minimal, store pending remainder on `User` (new field). Update settings UI to edit rate.
6. Update export/import to include new fields (menu image_url, household contribution_rate, user pending contribution counter if added). Update help/settings copy if needed. Add tests in `tests/` verifying new behaviors and run `python -m pytest`.

## Validation and Acceptance

- Starting the app, log in as root using the seeded credentials; navigating to `/admin` shows household and user management. Non-admin users are redirected/denied.
- Creating a menu allows attaching an image, adding more than five ingredients by adding rows, and unit fields autofill when selecting ingredients with stored units. Saved menus display the uploaded image and units.
- Editing/creating menus and meal plans increments contribution counters; after the configured rate (default 10 actions), the user earns 1 point recorded in `PointTransaction`. Changing the rate in settings adjusts future awards.
- Data export/import round-trips new fields without errors. All tests pass: `python -m pytest`.

## Idempotence and Recovery

Model changes are additive and should not break existing data; root creation should check for existing root email to avoid duplicates. Upload handling should overwrite the menu image when re-uploaded. Admin CRUD operations should validate input and flash errors instead of crashing. Contribution counters should handle remainder across multiple actions safely.

## Artifacts and Notes

- Use `python -m pytest` for validation.
- Keep image uploads under `app/static/uploads` with unique filenames.

## Interfaces and Dependencies

- FastAPI routes in `app/main.py` using SQLModel session dependency.
- Templates under `app/templates` and CSS under `app/static/style.css` for admin/menu UI.
- Utilize existing `store_instruction_upload` pattern for saving menu images.

