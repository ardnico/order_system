from sqlmodel import select

from app.models import (
    DishType,
    Household,
    MealPlan,
    MealPlanDay,
    MealSetRequirement,
    MealSetTemplate,
    Menu,
    MenuIngredient,
    Task,
    TaskTemplate,
    User,
)


def register_default(client):
    client.post(
        "/register",
        data={
            "display_name": "User",
            "email": "user@example.com",
            "password": "pw",
            "create_household": "1",
            "household_name": "Home",
            "join_code": "code",
        },
    )


def test_task_categories_filter_and_dropdown(client):
    register_default(client)
    # Create templates with seeded categories
    client.post(
        "/templates/tasks",
        data={
            "title": "Clean",
            "default_category": "cleaning",
            "default_points": 1,
            "relative_due_days": 1,
        },
    )
    client.post(
        "/templates/tasks",
        data={
            "title": "Cook",
            "default_category": "cooking",
            "default_points": 2,
            "relative_due_days": 1,
        },
    )

    resp = client.get("/templates/tasks", params={"category": "cleaning"})
    assert resp.status_code == 200
    assert "Clean" in resp.text
    assert "Cook" not in resp.text

    form_resp = client.get("/tasks/new")
    assert "cleaning" in form_resp.text
    assert "cooking" in form_resp.text


def test_meal_set_editing_updates_requirements(client, session):
    register_default(client)
    dish_type = session.exec(select(DishType).order_by(DishType.id)).first()
    dish_type_id = dish_type.id if dish_type else 1
    create_resp = client.post(
        "/settings/meal-sets",
        data={"name": "テストセット", "description": "desc", f"requirement_{dish_type_id}": "1"},
        follow_redirects=False,
    )
    assert create_resp.status_code in (200, 303)

    template = session.exec(select(MealSetTemplate).where(MealSetTemplate.name == "テストセット")).first()
    assert template is not None

    update_resp = client.post(
        f"/settings/meal-sets/{template.id}/edit",
        data={"name": "テストセット", "description": "update", f"requirement_{dish_type_id}": "2"},
        follow_redirects=False,
    )
    assert update_resp.status_code in (200, 303)
    session.expire_all()
    req = session.exec(select(MealSetRequirement).where(MealSetRequirement.meal_set_template_id == template.id)).first()
    assert req is not None
    assert req.required_count == 2


def test_font_and_localized_rewards(client, session):
    register_default(client)
    user = session.exec(select(User).where(User.email == "user@example.com")).first()
    household = session.get(Household, user.household_id)
    settings_resp = client.post(
        "/settings/language",
        data={
            "language": "ja",
            "theme": "sakura",
            "font": "serif",
            "household_name": household.name,
            "join_code": household.join_code,
            "contribution_rate": household.contribution_rate,
        },
        follow_redirects=False,
    )
    assert settings_resp.status_code in (200, 303)
    session.expire_all()
    household = session.get(Household, user.household_id)
    assert household.font == "serif"
    assert household.language == "ja"
    rewards_page = client.get("/rewards")
    assert "ごほうび" in rewards_page.text


def test_seeded_menus_expanded(client, session):
    register_default(client)
    menu_page = client.get("/menus")
    assert menu_page.status_code == 200
    assert "カレーライス" in menu_page.text or "唐揚げ" in menu_page.text


def test_task_points_prefilled_on_actions(client, session):
    register_default(client)
    task_resp = client.post(
        "/tasks/new",
        data={
            "title": "Test",
            "description": "",
            "category": "cleaning",
            "due_date": "2025-01-01",
            "due_time": "",
            "proposed_points": 5,
            "priority": 3,
            "assignee_user_id": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert task_resp.status_code in (200, 303)
    task = session.exec(select(Task).where(Task.title == "Test")).first()
    detail = client.get(f"/tasks/{task.id}")
    assert "value=\"5\"" in detail.text


def test_bowl_and_noodle_types_and_samples(client, session):
    register_default(client)
    client.get("/menus")
    user = session.exec(select(User).where(User.email == "user@example.com")).first()
    household = session.get(Household, user.household_id)
    types = {d.name for d in session.exec(select(DishType).where(DishType.household_id == household.id))}
    assert "Bowl" in types
    assert "Noodle" in types
    oyakodon = session.exec(select(Menu).where(Menu.name == "親子丼")).first()
    assert oyakodon is not None
    links = session.exec(select(MenuIngredient).where(MenuIngredient.menu_id == oyakodon.id)).all()
    assert links


def test_sample_meal_plan_seeded(client, session):
    register_default(client)
    resp = client.get("/meal-plans")
    assert resp.status_code == 200
    user = session.exec(select(User).where(User.email == "user@example.com")).first()
    household = session.get(Household, user.household_id)
    plan = session.exec(select(MealPlan).where(MealPlan.household_id == household.id)).first()
    assert plan is not None
    days = session.exec(select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id)).all()
    assert days
    assert any(d.dinner_menu_id for d in days)
