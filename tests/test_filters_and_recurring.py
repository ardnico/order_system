from datetime import date

from sqlmodel import Session, select

from app.models import RecurringTaskRule, Task, TaskTemplate


def register_user(client, name="Alice", email="alice@example.com"):
    return client.post(
        "/register",
        data={
            "display_name": name,
            "email": email,
            "password": "pw",
            "create_household": "1",
            "household_name": "Home",
            "join_code": "code",
        },
    )


def test_task_list_defaults_to_assigned(client, session: Session):
    register_user(client)
    client.post(
        "/tasks/new",
        data={
            "title": "Mine",
            "description": "",
            "category": "cleaning",
            "due_date": "2025-01-15",
            "proposed_points": 5,
            "priority": "medium",
        },
    )
    client.post(
        "/tasks/new",
        data={
            "title": "Unassigned",
            "description": "",
            "category": "cleaning",
            "due_date": "2025-01-15",
            "proposed_points": 3,
            "priority": "medium",
        },
    )
    # remove assignee from second task to verify filter hides it
    second_task = session.exec(select(Task).order_by(Task.id.desc())).first()
    second_task.assignee_user_id = None
    session.add(second_task)
    session.commit()

    resp_default = client.get("/tasks")
    assert "Mine" in resp_default.text
    assert "Unassigned" not in resp_default.text

    resp_all = client.get("/tasks?scope=all")
    assert "Unassigned" in resp_all.text


def test_recurring_rule_generates_tasks(client, session: Session):
    register_user(client)
    client.post(
        "/templates/tasks",
        data={
            "title": "Weekly Trash",
            "default_category": "cleaning",
            "default_points": 2,
            "relative_due_days": 0,
            "memo": "Take out trash",
        },
    )
    template = session.exec(select(TaskTemplate)).first()
    client.post(
        "/settings/recurring",
        data={
            "task_template_id": template.id,
            "frequency": "weekly",
            "next_run_date": date.today().isoformat(),
            "assignee_user_id": "",
        },
    )
    rule = session.exec(select(RecurringTaskRule)).first()
    assert rule is not None

    client.get("/")

    created_task = session.exec(select(Task).where(Task.task_template_id == template.id)).first()
    assert created_task is not None
    assert created_task.title == "Weekly Trash"
