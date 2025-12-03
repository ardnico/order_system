# Household Chore Board

A FastAPI-based web app for managing household chores as tasks with point rewards, templates, and reward usage, following `PROJECT_PLAN.md`.

## Features
- Household-scoped authentication with join codes.
- Task ordering lifecycle: create, claim, start, complete, approve (awards points), cancel.
- Task templates with defaults and relative due dates.
- Reward templates and reward usage requests with approval and point deduction.
- Point balances and history per user and household.
- Cute, pastel HTML UI with Japanese/English language toggle.
- Task assignment defaults and filters (assigned/all/completed) plus order-sheet view.
- Task template instructions with AsciiDoc-like steps and optional images.
- Recurring task rules per template with assignee targeting.

## Getting started
1. Install dependencies (Python 3.11+ recommended):
   ```bash
   pip install -r requirements.txt
   ```
2. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Open [http://localhost:8000/register](http://localhost:8000/register) to create the first household and user. Share the household join code with other users to let them join via the register page.

Environment variables:
- `DATABASE_URL` (optional): defaults to `sqlite:///order_system.db` in the repository root.
- `SESSION_SECRET` (optional): secret key for session cookies.

## Basic workflow
1. Register or log in to your household.
2. Create task templates for frequent chores (optional).
3. Create tasks from scratch or templates, assigning due dates and points.
4. Users claim tasks, mark them in progress, submit completion, and a partner approves to award points.
5. Create reward templates and submit reward usage requests; approvals deduct points.
6. Track balances and transaction history from the Point History page.

## Testing
Run the automated tests:
```bash
pytest
```

## Notes
- If the SQLite database becomes unusable during local development, stop the server, delete `order_system.db`, and restart the app to recreate tables.
- The app is intended for small household use and does not include external integrations.
- This repository vendors lightweight `httpx` and `itsdangerous` shims so tests can run without external downloads when network access is blocked. If you have internet access, installing the requirements will use the upstream packages instead.
