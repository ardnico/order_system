# Task categories, meal set editing, and UI localization improvements

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain this plan in accordance with .agent/PLANS.md.

## Purpose / Big Picture

Household users need more control over meal planning, task organization, and the interface look-and-feel. After this change, they can manage dish types and meal set templates directly from settings, pick UI fonts, view rewards and point history fully localized, and organize tasks/templates by registered categories with dropdown selection and filtering. Task templates become filterable by category, preset menus cover more dishes, and task points default sensibly when claiming or starting. Acceptance is demonstrated by creating/editing dish types and sets in settings, switching fonts, seeing localized reward/point pages in Japanese, selecting categories from dropdowns, filtering templates by category, seeing expanded preset menus, and observing task point defaults during claim/start workflows with tests passing.

## Progress

- [x] (2025-02-07 00:00Z) Initial plan drafted per PLANS.md.
- [x] (2025-02-07 00:45Z) Implemented models, seed data, font support, category/dish-type/meal-set management, and expanded preset menus.
- [x] (2025-02-07 01:25Z) Updated task/template flows, localization, template filtering, point defaults, and added coverage for categories, fonts, and presets.
- [x] (2025-02-07 01:30Z) Ran pytest successfully and captured results.

## Surprises & Discoveries

- Observation: None yet.
  Evidence: N/A.

## Decision Log

- Decision: Keep task categories as registered entities scoped to households with dropdown selection while storing the category name on tasks/templates for compatibility.
  Rationale: Minimizes migration risk and keeps filtering simple without changing existing task records.
  Date/Author: 2025-02-07 / assistant.

## Outcomes & Retrospective

Implemented configurable fonts, task categories with dropdowns and filtering, editable dish types and meal sets, expanded preset menus, and localized reward/point pages. Automated task point defaults now prefill proposed values on claim/start, and new tests cover the flows. All tests pass (pytest).

## Context and Orientation

Key files:
- `app/models.py` defines SQLModel tables for tasks, meal planning, and rewards. Task.category is a string; meal sets and dish types exist without editing UI; no task category model.
- `app/main.py` holds FastAPI routes, UI strings, seed functions, and helpers. Settings page lists unit options and meal sets/dish types but lacks editing forms or font selection. Rewards/points templates are English-only. Task creation/templates use free-text categories; template list lacks filtering.
- Templates under `app/templates/` include `settings.html`, `task_form.html`, `task_templates.html`, `rewards.html`, `points.html`, `base.html`, and meal/menu pages.
- Styles live in `app/static/style.css` and themes are applied via a body class. Fonts are fixed in CSS.
- Seed data for meal menus resides in `seed_default_menus` inside `app/main.py`.

## Plan of Work

First, extend data structures: add a TaskCategory model (household-scoped, name unique) and a Household.font choice. Update seed/setup helpers to ensure default categories and fonts, and expand preset menus. Next, enhance settings: allow creating/editing/deleting dish types and meal set templates with requirements, manage unit options, categories, and font selection. Wire routes to support these actions. Then, adjust task and template forms to use dropdowns for registered categories; add filter capability on task templates by category; ensure claim/start actions default actual points to configured values when optional inputs are blank, using template defaults where appropriate. Localize rewards and points pages via UI_STRINGS and template updates. Finally, add tests covering category dropdown behavior, template filtering, meal set editing, font preference propagation, localization, and seeded menus. Validate with pytest.

## Concrete Steps

1. Extend `app/models.py`: add `TaskCategory` table with household_id, name, created_at; add `font` field to `Household` with a default. Update `__all__` accordingly.
2. In `app/main.py`, expand UI_STRINGS for rewards/points labels and settings (fonts, categories). Add font choices list and helpers to read household font. Update `build_context` to supply font/theme choices and category data where needed.
3. Implement category utilities: CRUD routes for categories (likely under settings), ensure dropdown lists for tasks/templates use registered categories; retain free entry fallback only via managed categories. Seed default categories on household creation if none exist.
4. Enhance settings routes/templates: add forms to create/update/delete dish types and meal set templates (including requirements per dish type), manage categories, unit options, and font selection. Persist updates via new endpoints.
5. Update task/template routes and templates: use category dropdowns (with template default preselect), provide template list filter by category query param, and ensure claim/start point inputs prefill with task.proposed_points or template defaults as initial values.
6. Localize `rewards.html` and `points.html` using new UI strings; ensure points/rewards route contexts pass required data.
7. Expand `seed_default_menus` with more preset dishes and ensure seed helpers create unit options needed.
8. Add/adjust tests in `tests/` to cover new behaviors (category dropdowns, template filtering, font/dish-set management, localization labels rendering, preset menu count). Update existing tests if assumptions change.
9. Run `pytest`; capture output. Iterate if failures occur. Document surprises/decisions/outcomes.

## Validation and Acceptance

- Start app, set language to Japanese, navigate to Rewards and Points pages; verify headers/buttons are Japanese.
- In settings, create/edit/delete dish types and meal set templates; see changes reflected in meal plan selection options.
- Switch font in settings; observe CSS changes via rendered page class/style.
- Register task categories in settings; in task creation/template forms, categories appear as dropdown options; template list supports category filter showing only matching entries.
- Task claim/start actions show points inputs prefilled with proposed/template defaults when optional; no blank default.
- Preset menus include additional dishes visible on menu list for new household seeds.
- `pytest` passes.

## Idempotence and Recovery

Changes are additive to models and templates; rerunning seed helpers is safe because they check for existing records. Form submissions validate household ownership. If a form creates unintended data, delete via the corresponding delete forms. Database schema changes rely on SQLModel create_all; for existing local DBs, recreate the DB if columns are missing.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

- Task category dropdowns rely on a new `TaskCategory` model queried by household.
- Font selection uses a predefined set of font keys mapped to CSS font stacks.
- Dish type/set editing uses `MealSetTemplate` and `MealSetRequirement` records; requirements map dish types to required counts.
- Template filtering reads `default_category` on `TaskTemplate` and compares against selected category string.
