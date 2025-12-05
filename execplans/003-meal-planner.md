# Meal planning and shopping support module

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain this document according to .agent/PLANS.md.

## Purpose / Big Picture

Deliver the meal-planning and shopping support features outlined in PROJECT_PLAN.md Phase 1. Households can define menus with ingredients, assemble a dated meal plan covering lunch and dinner slots, and view an aggregated ingredient list for the selected plan to drive shopping. Users create and edit menus, assign them to days, and see totals per ingredient name and unit.

## Progress

- [x] (2025-12-06 00:00Z) Drafted ExecPlan describing meal planning, menu CRUD, and ingredient aggregation.
- [x] (2025-12-06 00:20Z) Implemented models for menus, ingredients, meal plans, and plan days.
- [x] (2025-12-06 00:30Z) Added menu helpers and ingredient aggregation utilities.
- [x] (2025-12-06 01:00Z) Built routes and templates for menus, meal plans, and ingredient lists.
- [x] (2025-12-06 01:10Z) Added tests for menu CRUD and ingredient aggregation.
- [x] (2025-12-06 01:12Z) Ran pytest and verified all tests pass.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Scope this iteration to Phase 1 behaviors (menus, meal plans, ingredient aggregation) without menu type filters or task auto-generation.
  Rationale: Keeps work bounded while matching PROJECT_PLAN.md Phase 1 acceptance.
  Date/Author: 2025-12-06 / assistant.

## Outcomes & Retrospective

Implemented the meal-planning module with menu CRUD, meal plan editing, and aggregated ingredient lists per PROJECT_PLAN.md Phase 1. Added helper utilities and tests to ensure menu ingredients persist and ingredient totals sum across plans. Pytest passes, confirming the new flows integrate with existing auth and session handling.

## Context and Orientation

The FastAPI app lives in `app/main.py` with SQLModel models in `app/models.py`. Templates are under `app/templates/` and static assets under `app/static/`. Authentication helpers reside in `app/auth.py`, and tests live in `tests/`. We already have household/user/task/reward flows. The project plan calls for adding a meal planning module with menus, ingredients, meal plans with day entries, and an aggregated shopping list. New database models and routes must integrate with existing session-based auth and template rendering.

## Plan of Work

1. Extend database models in `app/models.py` with Menu, Ingredient, MenuIngredient (linking menus to ingredients with quantity/unit), MealPlan (named plan with start/end dates and household ownership), and MealPlanDay (per-date entries storing lunch_menu_id and dinner_menu_id). Add relationships and helper properties where useful. Update `init_db` to create tables.
2. Add ingredient aggregation logic in a helper within `app/main.py` or a small utility to sum MenuIngredient quantities for all menus referenced by a MealPlan's days, grouped by ingredient name and unit. Provide functions to fetch menus list and ingredient totals for templates.
3. Create routes and templates:
   - Menu management: list existing menus, create new, edit existing, and delete. Forms capture name and ingredient rows (name, quantity, unit) with simple text fields and allow multiple ingredient rows.
   - Meal plan pages: list all plans for the household; create a new plan with name, start_date, end_date; view a plan showing each day in the range with lunch/dinner selectors for menus; submit updates to assign menus per slot.
   - Ingredient list view: for a given plan, show aggregated ingredients table with name, total quantity, and unit, plus a checkbox column for shopping.
4. Update navigation templates to link to menus, meal plans, and ingredients list. Style tables minimally in `app/static/style.css` if needed for readability.
5. Add tests under `tests/` covering menu CRUD endpoints, meal plan creation and day assignment, and ingredient aggregation totals from multiple days.
6. Run pytest and update Progress, Surprises, Decision Log (if new choices), and Outcomes with summary and next steps.

## Concrete Steps

1. Modify `app/models.py` to define Menu, Ingredient, MenuIngredient, MealPlan, MealPlanDay models using SQLModel. Ensure `init_db` creates tables.
2. In `app/main.py`, add helper functions for ingredient aggregation, menu retrieval, and ensure routes enforce logged-in household scope.
3. Implement FastAPI routes:
   - `/menus` (GET/POST) for list/create, `/menus/{menu_id}/edit` (GET/POST) for edit, `/menus/{menu_id}/delete` (POST) for removal.
   - `/meal-plans` list/create, `/meal-plans/{plan_id}` view/update day assignments, `/meal-plans/{plan_id}/ingredients` for aggregated list.
4. Create templates under `app/templates/` for menus list/form, meal plan list/new, meal plan detail/day assignment, and ingredient summary. Reuse base layout and include flashes/strings.
5. Add CSS tweaks if needed for the new tables and form layouts.
6. Add pytest cases in `tests/` using TestClient to validate menu CRUD, plan creation, day updates, and ingredient totals across menus. Use the in-memory DB fixture.
7. Run `pytest` from repo root; ensure tests pass.
8. Update this ExecPlan Progress and Outcomes to reflect completion and learning.

## Validation and Acceptance

After implementation, start the app (`uvicorn app.main:app --reload`) and:
- Create menus with ingredients via `/menus` and confirm list shows entries.
- Create a meal plan spanning dates, open its detail page, and assign lunch/dinner menus for each day; changes persist on refresh.
- View `/meal-plans/{id}/ingredients` to see aggregated ingredient totals; quantities sum when the same ingredient name/unit appears across selected menus.
- Run `pytest` and expect all tests, including new meal planning tests, to pass.

## Idempotence and Recovery

Model additions are additive; existing tables remain. Meal plan and menu CRUD operations are standard database writes and can be retried. Ingredient aggregation reads current plan state and is safe to re-run. In case of data issues, deleting the SQLite file resets state for local dev.

## Artifacts and Notes

To be populated with key outputs (pytest results, manual curl excerpts) once work completes.

## Interfaces and Dependencies

All changes stay within existing FastAPI/SQLModel stack. New models live in `app/models.py` and use existing `engine` from `app/db.py`. Routes reside in `app/main.py` with Jinja2 templates in `app/templates/`. No external dependencies are introduced beyond current requirements.
