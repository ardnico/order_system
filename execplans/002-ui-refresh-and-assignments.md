# Cute UI, localization, assignments, and recurring tasks

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain this document according to .agent/PLANS.md.

## Purpose / Big Picture

Deliver a more polished household chore board where families can use a cute, Japanese-friendly interface, assign tasks explicitly, and manage recurring chores and templates with detailed instructions and photos. Users should see their assigned tasks by default, filter task lists, edit tasks after creation, configure language preferences and auto-generation schedules, and view assigned tasks in an order-sheet style.

## Progress

- [x] (2025-12-03 00:00Z) Drafted ExecPlan describing UI refresh, localization, assignments, recurring tasks, and template enhancements.
- [x] Implemented backend model changes (household language, recurring rules, template instructions, task editing support fields).
- [x] Refreshed UI styling, navigation, localization hooks, and templates (cute theme, Japanese language option, order-sheet view).
- [x] Added task filters, assignment defaults, task edit forms, template editing, and instruction rendering with images.
- [x] Implemented recurring task scheduler hook and settings page for language and auto-generation rules.
- [x] Write/adjust tests and validate manually plus pytest.
- [x] (2025-12-04 00:00Z) Finalized cleanup by moving startup work to FastAPI lifespan and updating template responses to silence deprecation warnings.

## Surprises & Discoveries

- Observation: Test runs emit a remaining deprecation warning from passlib's crypt backend but do not block execution.
  Evidence: pytest warnings summary still notes the crypt deprecation after addressing FastAPI warnings.
- Observation: Starlette TemplateResponse now expects the Request as the first argument; updating call sites removes the warning spam during tests.
  Evidence: Warning text suggested replacing `TemplateResponse(name, {"request": request})` with `TemplateResponse(request, name)`; calls were updated accordingly.

## Decision Log

- Decision: Default new tasks to assign to the creator when no assignee is provided and show "assigned to me" as the default task list scope.
  Rationale: Ensures the list view stays focused on actionable items and matches the requirement for default assigned-task visibility.
  Date/Author: 2025-12-03 / assistant.
- Decision: Implement a lightweight AsciiDoc-like renderer in-app and allow optional image URLs for template instructions instead of adding heavy dependencies.
  Rationale: Keeps offline friendliness while fulfilling the requirement for procedural instructions with photos.
  Date/Author: 2025-12-03 / assistant.
- Decision: Trigger recurring task generation on dashboard and task-list access based on next_run_date rather than a background scheduler.
  Rationale: Avoids adding background workers while still honoring recurring generation through normal usage.
  Date/Author: 2025-12-03 / assistant.
- Decision: Replace the deprecated FastAPI on_event startup hook with a lifespan handler to run init_db once and clear test warnings.
  Rationale: Aligns with FastAPI guidance and keeps startup behavior explicit without altering runtime flow.
  Date/Author: 2025-12-04 / assistant.

## Outcomes & Retrospective

Delivered a pastel, bilingual UI with default assigned-task focus, filter pills, and editable tasks. Households can toggle Japanese/English, edit task and template details with AsciiDoc-like instructions and photos, and view an order-sheet style summary. Recurring rules generate tasks on dashboard/task access based on next_run_date. Added tests for assignment filtering and recurring creation; pytest passes, and app warnings are reduced to only the upstream passlib crypt notice.

## Context and Orientation

The FastAPI app lives in `app/main.py` with SQLModel models in `app/models.py`, templates in `app/templates/`, and CSS in `app/static/style.css`. Authentication and session helpers are in `app/auth.py`, and tests in `tests/`. Task templates currently support create/delete only; tasks have assignable fields but lack explicit assignment controls and editing. There is no localization support or recurring task scheduling. We will add household-level settings for language and recurring rules, enhance templates to render instructions with AsciiDoc-like markup and optional images, and redesign UI to be cute and Japanese-friendly.

## Plan of Work

1. Extend data models to support household settings (language preference), recurring task rules linked to templates, richer task templates (instructions text + optional image URL), and task editing. Update initialization where needed.
2. Add helpers in `app/main.py` for localization (simple translation dictionary and per-household language selection), instruction rendering (safe HTML conversion of AsciiDoc-like syntax and image embedding), and recurring task generation (check rules on dashboard/tasks access and create tasks accordingly).
3. Implement routes and templates:
   - Settings page to toggle language (English/Japanese), manage recurring task rules (frequency, template, assignee), and preview language change.
   - Task list defaulting to assigned tasks with filter controls (all, completed) and ability to set assignee during creation and editing.
   - Task edit form and order-sheet-style view for assigned tasks.
   - Task template edit form plus instruction fields (AsciiDoc-like) and image support.
4. Refresh CSS and template styling to a cute, pastel theme with playful accents; ensure language texts adjust when Japanese is selected.
5. Update README or inline help if needed and add/adjust tests for new behaviors (assignment filter default, recurring creation hook, template instruction rendering) and run pytest.
6. Update ExecPlan sections with discoveries, decisions, and outcomes.

## Concrete Steps

- Modify `app/models.py` to add `language` to `Household`, `instructions` and `instruction_image_url` to `TaskTemplate`, and new `RecurringTaskRule` model. Ensure DB init creates new tables/columns.
- Add localization utilities and translation dictionary in `app/main.py`; pass `ui_strings` and `language` to templates via context.
- Implement instruction rendering helper (AsciiDoc-like) and include output in task template and task detail views.
- Create settings routes/templates for language toggle and recurring rule CRUD; run recurring generation check on dashboard/tasks access.
- Enhance task creation/editing routes to select assignee and edit after creation; adjust task list default filter and filters for all/completed.
- Add order-sheet style view for assigned tasks and template editing routes/forms.
- Update CSS for cute pastel styling and adjust templates for localization strings.
- Add tests for assignment default filter and recurring generation logic; run `pytest`.

## Validation and Acceptance

- Language setting in settings page switches UI labels between English/Japanese across navigation and key headings.
- Task list defaults to showing tasks assigned to the current user; filter controls allow switching to all tasks and completed tasks.
- Tasks can be assigned during creation or editing, and edits persist.
- Task templates can be edited and include instruction text (AsciiDoc-like) and optional image display in task detail/template views.
- Settings allow configuring recurring tasks (frequency, next run), and accessing dashboard/tasks auto-creates due tasks from rules.
- Assigned tasks have an order-sheet-like view with key details and assignee info.
- Styling is visibly cuter with pastel palette and rounded cards.
- pytest passes.

## Idempotence and Recovery

Model changes are additive; existing data remains valid with default language/blank instructions. Recurring generation checks are guarded by `next_run_date` updates to avoid duplicates. Forms validate presence of required fields and redirect with flashes on errors. The settings page allows disabling rules to stop generation. Re-running pages safely regenerates only when `next_run_date` is due.

## Artifacts and Notes

To be populated with relevant diffs or outputs after implementation.

## Interfaces and Dependencies

New model `RecurringTaskRule` in `app/models.py` with fields: id, household_id, task_template_id (FK), frequency (daily/weekly/monthly), assignee_user_id (optional), next_run_date (date), active (bool), created_at.
Add `language` (str, default `en`) to Household and instruction fields to TaskTemplate. Localization uses in-app dictionary; no external libs. Recurring generation helper resides in `app/main.py` and is invoked from dashboard/task list routes.
