# Ingredients library, data export/import, and charming help page

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain this document in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Enable households to manage a reusable library of food ingredients, back up and restore key household data through export/import, and present a friendlier, cute help page that still guides users clearly. After completion, users can add ingredients directly, reuse them in menus and meal plans, download their household configuration as JSON, re-import it safely, and explore the help page for an inviting overview.

## Progress

- [x] (2025-03-01 00:00Z) Drafted initial ExecPlan.
- [x] (2025-03-01 00:40Z) Implemented ingredient library UI/endpoints and menu ingredient picker.
- [x] (2025-03-01 01:15Z) Added household export/download and import/upload flows with validation and settings UI.
- [x] (2025-03-01 01:30Z) Redesigned help page styling/content with cute layout.
- [x] (2025-03-01 01:55Z) Added ingredient/export-import tests and ran pytest.
- [ ] Update retrospective and finalize.

## Surprises & Discoveries

- Observation: Adding `{% extends %}` twice in `menus/list.html` caused a Jinja runtime error until the duplicate was removed.
  Evidence: Pytest failures complaining about "extended multiple times" during initial run.

## Decision Log

- Decision: Limit export/import to household-scoped configuration (ingredients, unit options, dish types, menus with ingredient mapping, meal set templates/requirements, task templates/categories, recurring rules, reward templates) to avoid leaking user credentials or cross-household data. Preserve references via names, not raw IDs, to stay portable inside the same household.
  Rationale: Keeps backups useful without handling user accounts or sensitive auth; name-based mapping survives ID changes across imports.
  Date/Author: 2025-03-01 / coding agent.

## Outcomes & Retrospective

Ingredient management now exists with deletion guards, menus can reuse ingredients via suggestions, data export/import covers key household configuration, and the help page presents a cuter guided layout. Future follow-up could translate flash messages for ingredient CRUD fully and add CSV variants for export/import if needed.

## Context and Orientation

The FastAPI app lives in `app/main.py`, using SQLModel models from `app/models.py`. Templating uses Jinja2 in `app/templates/`, with shared styling from `app/static/style.css`. Menus and meal planning already store ingredients via `Ingredient`, `Menu`, and `MenuIngredient` models but lack a direct ingredient management screen. Data seeds for dish types and units are in helper functions such as `ensure_meal_seed_data`. Authentication and household scoping rely on `require_user` in `app/auth.py`. The help page is `app/templates/help.html`.

## Plan of Work

First, add an ingredient library page (`/ingredients`) that lists existing ingredients for the household and allows creation of new ones with a chosen unit option. Use a POST handler to create (or deduplicate) entries and a delete handler to remove ingredients not referenced by menus. Update menu create/edit forms to surface existing ingredient names via datalist or select widgets and align units with unit options to encourage reuse. Adjust meal-plan aggregation to respect any new units.

Second, implement export/import. Provide a GET endpoint to download household configuration as JSON (content-disposition attachment) summarizing unit options, dish types, ingredients, menus (with ingredient links), meal set templates and requirements, task categories, task templates (including recurrence rules), and reward templates. Provide a POST endpoint accepting an uploaded JSON file; validate schema, then upsert data: create/update unit options, dish types, ingredients; recreate menus and their ingredients by matching names; recreate meal set templates/requirements; upsert task categories/templates and recurring rules; upsert reward templates. Reject malformed files with flash errors and avoid touching user accounts or point transactions. Encapsulate import/export strings in UI translations and place controls within a new “Data” card under settings.

Third, redesign `help.html` with playful visuals (pastel gradient, icon badges, step cards) while keeping content concise in Japanese-first text, adding quick links and emoji. Add supporting CSS in `app/static/style.css` and ensure translations for new copy in `UI_STRINGS` in `app/main.py`. Integrate navigation styling so the help page feels inviting yet clear.

Fourth, add server-side and template translations for new labels (ingredient management, export/import, help content) ensuring default Japanese strings. Keep flash messages localized where feasible.

Finally, add tests covering ingredient creation and import/export JSON round-trip using the existing FastAPI test client where possible. Run `python -m pytest` to verify.

## Concrete Steps

1. Create ingredient management routes in `app/main.py`: GET `/ingredients` (list + form), POST `/ingredients` (create deduped by name/unit within household), POST `/ingredients/{id}/delete` (delete when unreferenced). Add template `app/templates/ingredients.html` and link from navigation or settings. Wire context with unit options and strings.
2. Update menu forms (`app/templates/menus/list.html`, `app/templates/menus/edit.html`) to use datalist/select populated from household ingredients for names and to default units from unit options; keep optional free text but bias reuse.
3. Add export/download endpoint GET `/data/export` returning JSON attachment plus POST `/data/import` accepting UploadFile; implement serializer/deserializer helpers in `app/main.py` to convert between models and JSON objects using name-based lookups. Add UI card in `app/templates/settings.html` for export/import with instructions and flash errors/successes.
4. Refresh `help.html` with cute layout: hero banner, icon sections, call-to-action buttons for register/login, and pastel styling. Extend `app/static/style.css` with accent classes and responsive grid tweaks.
5. Expand `UI_STRINGS` in `app/main.py` for new labels and messages (Japanese default, English secondary). Ensure `build_context` and templates use these strings.
6. Add tests in `tests/` to cover ingredient creation endpoint and export/import flow (serialize data, clear tables, import, verify). Run pytest.

## Validation and Acceptance

- Visiting `/ingredients` as an authenticated user shows existing ingredients and allows adding a named ingredient with a unit; duplicates are prevented; deleting an unused ingredient removes it. Menu forms show existing ingredient names via suggestions.
- Clicking “データを書き出す” downloads a JSON file; uploading the same file to “データを取り込む” restores the records (unit options, dish types, ingredients, menus with ingredient mapping, task categories/templates with recurrence, reward templates) for the household without altering users or points.
- The help page renders with the new cute layout, Japanese-first copy, and navigation links invite exploration.
- `python -m pytest` passes.

## Idempotence and Recovery

Ingredient creation is idempotent by name/unit; repeated posts yield the same stored item. Import validates payload structure and aborts without changes on failure. Export is read-only. If an import partially fails, rerun after correcting the file; helper functions should wrap operations in household-scoped upserts to stay consistent.

## Artifacts and Notes

- None yet.

## Interfaces and Dependencies

- New FastAPI routes `/ingredients`, `/data/export`, and `/data/import` in `app/main.py` using existing `Session`, `require_user`, and `build_context` helpers.
- Templates `app/templates/ingredients.html`, updates to `app/templates/menus/*.html`, `app/templates/help.html`, and `app/templates/settings.html`.
- Styling in `app/static/style.css` for help and ingredient cards.
- Tests added to `tests/` using existing pytest + FastAPI test client patterns.
