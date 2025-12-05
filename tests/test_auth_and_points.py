from sqlmodel import Session, select

from app.auth import hash_password, verify_password
from app.models import PointTransaction, RewardUse, Task, TaskStatus


def test_password_hashing_roundtrip():
    password = "secret123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_task_approval_awards_points(client, session: Session):
    client.post(
        "/register",
        data={
            "display_name": "Alice",
            "email": "alice@example.com",
            "password": "pw",
            "create_household": "1",
            "household_name": "Home",
            "join_code": "code",
        },
    )
    create_resp = client.post(
        "/tasks/new",
        data={
            "title": "Clean",
            "description": "",
            "category": "cleaning",
            "due_date": "2025-01-15",
            "proposed_points": 10,
            "priority": 3,
        },
        follow_redirects=False,
    )
    task_id = int(create_resp.headers["location"].split("/")[-1])
    client.post(f"/tasks/{task_id}/action", data={"action": "claim"})
    client.post(f"/tasks/{task_id}/action", data={"action": "start"})
    client.post(f"/tasks/{task_id}/action", data={"action": "complete"})
    client.post(
        f"/tasks/{task_id}/action",
        data={"action": "approve", "actual_points": 15},
    )

    session.expire_all()
    task = session.exec(select(Task)).first()
    assert task.status == TaskStatus.approved
    tx = session.exec(select(PointTransaction)).first()
    assert tx.amount == 15


def test_reward_approval_deducts_points(client, session: Session):
    client.post(
        "/register",
        data={
            "display_name": "Bob",
            "email": "bob@example.com",
            "password": "pw",
            "create_household": "1",
            "household_name": "Home",
            "join_code": "code",
        },
    )
    client.post(
        "/rewards/templates",
        data={"title": "Movie", "cost_points": 8},
    )
    client.post(
        "/rewards/use",
        data={"title": "Movie", "cost_points": 8},
    )
    # Approve the first reward
    reward_use = session.exec(select(RewardUse)).first()
    reward_use_id = reward_use.id
    client.post(
        f"/rewards/use/{reward_use_id}/action",
        data={"action": "approve"},
    )
    session.expire_all()
    tx = session.exec(select(PointTransaction)).first()
    assert tx.amount == -8
