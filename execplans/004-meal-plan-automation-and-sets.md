# Meal plan automation, set-based selection, and configurable units

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: .agent/PLANS.md. Maintain this plan in accordance with that guidance.

## Purpose / Big Picture

Enable households to pre-register menus with dish types, pick set templates that require specific dish counts per meal slot, and automatically create cooking tasks on the day a planned meal occurs. Users should configure recurring task generation for meal prep, choose ingredient units from a dropdown with configurable options, and seed the app with example menus and sets so planners can start immediately. Success looks like: selecting an A set for lunch surfaces soup/main/side pickers, saving the plan records those menu choices, and when the date arrives a task per meal slot appears with due date today. Ingredient forms use a dropdown whose options are manageable in settings.

## Progress

- [x] (2025-05-17 00:00Z) Drafted initial plan covering meal automation, set selection, and unit options.
- [x] (2025-05-17 01:10Z) Implemented models/seeds for dish types, unit options, set templates, selections, and meal-linked tasks.
- [x] (2025-05-17 01:25Z) Wired menu CRUD/UI to dish types and unit dropdowns with settings-driven unit options.
- [x] (2025-05-17 01:40Z) Built meal plan set selection UI, persistence, aggregation, and automatic meal prep task creation with tests.
- [x] (2025-05-17 01:45Z) Validated flows via pytest and refreshed plan outcomes.

## Surprises & Discoveries

- Seeded sample menus populate the database immediately, so tests must target menus by name rather than assuming an empty set.

## Decision Log

- Decision: Store meal plan dish picks in a dedicated `MealPlanSelection` table keyed by slot and dish type rather than overloading existing lunch/dinner fields.
  Rationale: Keeps set-based requirements flexible (multiple sides, etc.) without breaking existing menu references.
  Date/Author: 2025-05-17 / assistant

## Outcomes & Retrospective

- Added configurable dish types, unit options, set templates, and seeded menus to accelerate planning. Meal plans now capture per-slot sets and dish selections, aggregate ingredients across those picks, and create meal prep tasks automatically on the scheduled day. Unit options are maintained in settings and surfaced in menu forms. Tests cover new flows.

## Context and Orientation

Key files: `app/models.py` defines SQLModel tables for tasks, menus, ingredients, and meal plans. `app/main.py` hosts FastAPI routes, helper functions (`ensure_meal_plan_days`, `aggregate_meal_plan_ingredients`, `run_recurring_rules`), and dashboard/task/meal-plan/menu views. Templates under `app/templates` render menus (`menus/*.html`) and meal plans (`meal_plans/*.html`). Tests live in `tests/`, including meal planner coverage in `tests/test_meal_plans.py`. The database initializes via `app/db.py` calling `SQLModel.metadata.create_all` without migrations.

Current meal planning stores one lunch and one dinner menu per `MealPlanDay` but lacks dish-type granularity, set templates, or automatic task creation. Ingredients accept free-text units, and recurring rules exist for generic task templates via `RecurringTaskRule` but not meal-derived tasks.

## Plan of Work

1. Extend domain models to support dish types, meal set templates, unit options, and per-slot dish selections. Add enums/fields for meal slots on tasks to link generated tasks to meal plan days. Include seed helpers for default dish types, unit options, and sample menus/sets. Update aggregation helpers to account for multiple dish selections per slot.
2. Update menu CRUD to assign a dish type and use a dropdown of unit options for ingredients. Add settings UI and handlers to manage available unit options (add/remove/activate) scoped per household.
3. Enhance meal plan UI to choose a set template per meal slot (lunch/dinner) and render dish selectors per required type/count. Persist selections in new tables, allow overriding menus manually, and reflect them in the meal plan detail and ingredient aggregation views.
4. Implement automatic task generation: on each dashboard/tasks/settings visit, create tasks for meal plan days scheduled for today that have set selections. Tasks should be created once per slot with clear titles summarizing the set and menus, linked to the meal plan day/slot to prevent duplication. Provide ability to configure recurring meal prep task rules (frequency/assignee/start date) akin to existing recurring rules but scoped to meal planning.
5. Expand tests to cover menu dish type/unit validations, meal plan set selection persistence, ingredient aggregation with per-type selections, and automatic task creation on the target day. Verify UI context data and helper outputs. Update templates for dropdowns and selection lists accordingly.

## Concrete Steps

- Model updates: edit `app/models.py` to add `DishType`, `UnitOption`, `MealSetTemplate`, `MealSetRequirement`, `MealPlanSelection`, and a `MealSlot` enum. Add optional `dish_type_id` to `Menu`, unit option FK on `MenuIngredient` or store unit string from options, and `meal_plan_day_id` + `meal_slot` on `Task` for linkage. Include helper functions to seed default dish types, unit options, and sample menus/sets per household.
- Data helpers: in `app/main.py`, create utilities to fetch unit options, dish types, set templates, and to save selections. Update `aggregate_meal_plan_ingredients` to include `MealPlanSelection` across slots. Adjust `ensure_meal_plan_days` to initialize selection rows as needed.
- Menu UI & handlers: modify `/menus` templates to show dish type dropdown, ingredient unit dropdown, and allow adding unit options via settings. Update POST handlers to validate dish types and units, persisting menu ingredients accordingly.
- Settings UI: extend `settings.html` to manage unit options (list existing, add new) and display dish types/set templates (if editable) along with recurring meal task rules. Add routes to create/update unit options and meal set templates as needed.
- Meal plan UI: redesign `meal_plans/detail.html` to choose a set per meal slot and render per-dish selection widgets according to the set requirements. Persist via an updated POST handler that stores set choice and per-type menu selections in `MealPlanSelection`. Reflect selections in detail and `ingredients.html` summary.
- Task automation: add a scheduler-like function invoked with page hits (dashboard/tasks) that inspects `MealPlanDay` entries for today, reads set selections, and creates one Task per slot with a summary title, linking via new fields to avoid duplicates. Provide configuration for recurring meal task rules (frequency, start date, assignee) if separate from generic recurring rules.
- Tests: expand `tests/test_meal_plans.py` and add new tests for unit options and task creation. Ensure ingredient aggregation counts multiples per set. Run `pytest` to confirm.

## Validation and Acceptance

- Start the app, create a meal plan with a lunch set A requiring soup/main/side selections; save with specific menus typed by dish type. Reload detail to see selections persisted and ingredient aggregation reflecting all chosen dishes.
- On the day matching the plan, visiting the dashboard auto-generates tasks labeled for lunch/dinner preparation with due_date today and linked to the plan day. Refreshing does not duplicate tasks.
- Menu forms show unit dropdown populated from settings; adding a new unit in settings makes it appear in the menu ingredient form.
- Tests `pytest` pass, including new cases covering set selection persistence and auto task generation.

## Idempotence and Recovery

Plan changes are additive. Rerunning seed helpers should avoid duplicates by checking household-bound names. Task generation guarded by the `meal_plan_day_id` and `meal_slot` fields to prevent duplication on repeated visits. If schema changes require DB reset, removing `order_system.db` and rerunning init will recreate tables; document any data migrations inline.

## Artifacts and Notes

- Add minimal example transcripts in code comments or tests showing generated tasks titles and selection payloads.

## Interfaces and Dependencies

- New enums/classes: `app.models.MealSlot` for "lunch"/"dinner"; `DishType` (id, household_id, name, description); `UnitOption` (id, household_id, name, active); `MealSetTemplate` (id, household_id, name); `MealSetRequirement` (set_template_id, dish_type_id, required_count); `MealPlanSelection` (meal_plan_day_id, meal_slot, dish_type_id, menu_id, position).
- Task linking: extend `Task` with `meal_plan_day_id: Optional[int]` (FK) and `meal_slot: Optional[MealSlot]` to track generated tasks.
- Routes/UI must serialize/deserialize using these names consistently to keep templates and handlers aligned.
