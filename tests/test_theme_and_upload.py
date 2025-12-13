from sqlmodel import select

from app.models import Household, TaskTemplate, User
from tests.test_filters_and_recurring import register_user


def test_theme_preference_applies_to_pages(client, session):
    register_user(client)
    user = session.exec(select(User).where(User.email == "alice@example.com")).first()
    household = session.get(Household, user.household_id)
    client.post(
        "/settings/language",
        data={
            "language": "ja",
            "theme": "mint",
            "font": household.font,
            "household_name": household.name,
            "join_code": household.join_code,
            "contribution_rate": household.contribution_rate,
        },
    )

    session.expire_all()
    household = session.get(Household, user.household_id)
    assert household.theme == "mint"

    resp = client.get("/tasks")
    assert "theme-mint" in resp.text
    assert "タスク" in resp.text  # localized heading present


def test_instruction_image_upload_embeds_in_template(client, session):
    register_user(client)
    resp = client.post(
        "/templates/tasks",
        data={
            "title": "Photo chore",
            "default_category": "cleaning",
            "default_points": 2,
            "relative_due_days": 1,
            "memo": "with photo",
            "instructions": "= Step\n* wipe",
        },
        files={"instruction_image_file": ("sample.png", b"fake", "image/png")},
    )
    assert resp.status_code in (200, 303)

    template = session.exec(
        select(TaskTemplate).where(TaskTemplate.title == "Photo chore")
    ).first()
    assert template is not None
    assert template.instruction_image_url is not None
    assert template.instruction_image_url.startswith("/static/uploads/")
    assert "image::/static/uploads/" in (template.instructions or "")
