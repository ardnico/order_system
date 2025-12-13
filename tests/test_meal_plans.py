from sqlmodel import select

from datetime import date

from sqlmodel import select

from app.main import aggregate_meal_plan_ingredients, run_meal_plan_tasks
from app.models import (
    DishType,
    MealPlan,
    MealPlanDay,
    MealPlanSelection,
    MealSetTemplate,
    MealSlot,
    Menu,
    MenuIngredient,
    Task,
    User,
)


def register_default(client):
    client.post(
        "/register",
        data={
            "display_name": "Cook",
            "email": "cook@example.com",
            "password": "pw",
            "create_household": "1",
            "household_name": "Home",
            "join_code": "code",
        },
    )


def test_menu_creation_persists_ingredients(client, session):
    register_default(client)
    user = session.exec(select(User).where(User.email == "cook@example.com")).first()
    soup_type = session.exec(select(DishType).where(DishType.name == "Soup")).first()
    resp = client.post(
        "/menus",
        data={
            "name": "Curry",
            "dish_type_id": soup_type.id if soup_type else "",
            "ingredient_names": ["Onion"],
            "ingredient_quantities": ["1.5"],
            "ingredient_units": ["個"],
        },
        files={},
    )
    assert resp.status_code in (200, 303)

    session.expire_all()
    menu = session.exec(select(Menu).where(Menu.name == "Curry", Menu.household_id == user.household_id)).first()
    assert menu is not None
    links = session.exec(select(MenuIngredient).where(MenuIngredient.menu_id == menu.id)).all()
    assert len(links) == 1
    assert links[0].quantity == 1.5


def test_meal_plan_aggregation(client, session):
    register_default(client)
    user = session.exec(select(User).where(User.email == "cook@example.com")).first()
    # Create two menus with overlapping ingredient names/units
    soup_type = session.exec(select(DishType).where(DishType.name == "Soup")).first()
    main_type = session.exec(select(DishType).where(DishType.name == "Main")).first()
    client.post(
        "/menus",
        data={
            "name": "Soup",
            "dish_type_id": soup_type.id if soup_type else "",
            "ingredient_names": ["Onion"],
            "ingredient_quantities": ["1"],
            "ingredient_units": ["個"],
        },
        files={},
    )
    client.post(
        "/menus",
        data={
            "name": "Stew",
            "dish_type_id": main_type.id if main_type else "",
            "ingredient_names": ["Onion"],
            "ingredient_quantities": ["2"],
            "ingredient_units": ["個"],
        },
        files={},
    )
    plan_resp = client.post(
        "/meal-plans",
        data={"name": "Week", "start_date": "2025-01-01", "end_date": "2025-01-02"},
        follow_redirects=False,
    )
    assert plan_resp.status_code in (200, 303)

    session.expire_all()
    plan = session.exec(select(MealPlan).where(MealPlan.household_id == user.household_id)).first()
    soup_menu = session.exec(select(Menu).where(Menu.name == "Soup", Menu.household_id == user.household_id)).first()
    stew_menu = session.exec(select(Menu).where(Menu.name == "Stew", Menu.household_id == user.household_id)).first()
    set_template = session.exec(select(MealSetTemplate).where(MealSetTemplate.household_id == user.household_id)).first()
    days = session.exec(select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id).order_by(MealPlanDay.day_date)).all()

    data = []
    for idx, day in enumerate(days):
        data.append(("day_dates", str(day.day_date)))
        data.append(("lunch_menu_ids", ""))
        data.append(("dinner_menu_ids", ""))
        data.append(("lunch_set_ids", set_template.id if set_template else ""))
        data.append(("dinner_set_ids", ""))
        # lunch selections align with default Aセット requirements (Soup/Main/Side)
        data.append((f"lunch_selection-{idx}-{soup_type.id}", soup_menu.id))
        data.append((f"lunch_selection-{idx}-{main_type.id}", stew_menu.id))
    update_resp = client.post(f"/meal-plans/{plan.id}", data=data)
    assert update_resp.status_code in (200, 303)

    session.expire_all()
    refreshed_plan = session.get(MealPlan, plan.id)
    totals = aggregate_meal_plan_ingredients(session, refreshed_plan)
    onion = next((t for t in totals if t["name"] == "Onion"), None)
    assert onion is not None
    assert onion["quantity"] == 3

    ingredients_page = client.get(f"/meal-plans/{plan.id}/ingredients")
    assert ingredients_page.status_code == 200
    assert "Onion" in ingredients_page.text


def test_meal_plan_tasks_create_on_day(client, session):
    register_default(client)
    user = session.exec(select(User).where(User.email == "cook@example.com")).first()
    soup_type = session.exec(select(DishType).where(DishType.name == "Soup")).first()
    set_template = session.exec(select(MealSetTemplate).where(MealSetTemplate.household_id == user.household_id)).first()
    client.post(
        "/menus",
        data={
            "name": "Day Soup",
            "dish_type_id": soup_type.id if soup_type else "",
            "ingredient_names": ["Onion"],
            "ingredient_quantities": ["1"],
            "ingredient_units": ["個"],
        },
        files={},
    )
    menu = session.exec(select(Menu).where(Menu.name == "Day Soup", Menu.household_id == user.household_id)).first()
    plan_resp = client.post(
        "/meal-plans",
        data={"name": "Today", "start_date": date.today(), "end_date": date.today()},
        follow_redirects=False,
    )
    assert plan_resp.status_code in (200, 303)

    session.expire_all()
    plan = session.exec(select(MealPlan).where(MealPlan.household_id == user.household_id)).first()
    day = session.exec(select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id)).first()
    data = [
        ("day_dates", str(day.day_date)),
        ("lunch_menu_ids", ""),
        ("dinner_menu_ids", ""),
        ("lunch_set_ids", set_template.id if set_template else ""),
        ("dinner_set_ids", ""),
        (f"lunch_selection-0-{soup_type.id}", menu.id),
    ]
    client.post(f"/meal-plans/{day.meal_plan_id}", data=data)

    session.expire_all()
    user = session.exec(select(User).where(User.email == "cook@example.com")).first()
    run_meal_plan_tasks(session, user.household_id, user.id)
    tasks = session.exec(select(Task).where(Task.meal_plan_day_id == day.id)).all()
    assert tasks
    assert tasks[0].meal_slot == MealSlot.lunch
