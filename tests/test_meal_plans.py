from sqlmodel import select

from app.main import aggregate_meal_plan_ingredients
from app.models import MealPlan, MealPlanDay, Menu, MenuIngredient


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
    resp = client.post(
        "/menus",
        data=[
            ("name", "Curry"),
            ("ingredient_names", "Onion"),
            ("ingredient_quantities", "1.5"),
            ("ingredient_units", "pc"),
        ],
    )
    assert resp.status_code in (200, 303)

    session.expire_all()
    menu = session.exec(select(Menu)).first()
    assert menu is not None
    links = session.exec(select(MenuIngredient).where(MenuIngredient.menu_id == menu.id)).all()
    assert len(links) == 1
    assert links[0].quantity == 1.5


def test_meal_plan_aggregation(client, session):
    register_default(client)
    # Create two menus with overlapping ingredient names/units
    client.post(
        "/menus",
        data=[
            ("name", "Soup"),
            ("ingredient_names", "Onion"),
            ("ingredient_quantities", "1"),
            ("ingredient_units", "pc"),
        ],
    )
    client.post(
        "/menus",
        data=[
            ("name", "Stew"),
            ("ingredient_names", "Onion"),
            ("ingredient_quantities", "2"),
            ("ingredient_units", "pc"),
        ],
    )
    plan_resp = client.post(
        "/meal-plans",
        data={"name": "Week", "start_date": "2025-01-01", "end_date": "2025-01-02"},
        follow_redirects=False,
    )
    assert plan_resp.status_code in (200, 303)

    session.expire_all()
    plan = session.exec(select(MealPlan)).first()
    menus = session.exec(select(Menu).order_by(Menu.name)).all()
    days = session.exec(select(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id).order_by(MealPlanDay.day_date)).all()

    data = []
    for idx, day in enumerate(days):
        data.append(("day_dates", str(day.day_date)))
        data.append(("lunch_menu_ids", menus[0].id if idx == 0 else ""))
        data.append(("dinner_menu_ids", menus[1].id if idx == 1 else ""))
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
