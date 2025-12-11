import json
from sqlmodel import select

from app.models import Ingredient, Menu, MenuIngredient


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


def test_ingredient_add_and_protect_delete(client, session):
    register_default(client)
    create_resp = client.post(
        "/ingredients",
        data={"name": "にんじん", "unit": "本"},
        follow_redirects=False,
    )
    assert create_resp.status_code in (200, 303)
    carrot = session.exec(select(Ingredient).where(Ingredient.name == "にんじん")).first()
    assert carrot is not None
    carrot_id = carrot.id

    client.post(
        "/menus",
        data={
            "name": "にんじんスープ",
            "description": "test",
            "dish_type_id": "",
            "ingredient_names": ["にんじん"],
            "ingredient_quantities": ["2"],
            "ingredient_units": ["本"],
        },
        files={},
        follow_redirects=False,
    )
    block_resp = client.post(f"/ingredients/{carrot_id}/delete", follow_redirects=False)
    assert block_resp.status_code in (200, 303)
    session.expire_all()
    still_there = session.get(Ingredient, carrot_id)
    assert still_there is not None

    # Remove menu to allow deletion
    for entry in session.exec(select(MenuIngredient)).all():
        session.delete(entry)
    for menu in session.exec(select(Menu)).all():
        session.delete(menu)
    session.commit()
    delete_resp = client.post(f"/ingredients/{carrot_id}/delete", follow_redirects=False)
    assert delete_resp.status_code in (200, 303)
    session.expire_all()
    assert session.get(Ingredient, carrot_id) is None


def test_export_and_import_round_trip(client, session):
    register_default(client)
    client.post("/ingredients", data={"name": "りんご", "unit": "個"}, follow_redirects=False)
    client.post(
        "/menus",
        data={
            "name": "アップルパイ",
            "description": "甘い",
            "dish_type_id": "",
            "ingredient_names": ["りんご"],
            "ingredient_quantities": ["3"],
            "ingredient_units": ["個"],
        },
        files={},
        follow_redirects=False,
    )

    export_resp = client.get("/data/export")
    assert export_resp.status_code == 200
    payload = export_resp.json()

    for entry in session.exec(select(MenuIngredient)).all():
        session.delete(entry)
    for menu in session.exec(select(Menu)).all():
        session.delete(menu)
    for ing in session.exec(select(Ingredient)).all():
        session.delete(ing)
    session.commit()

    files = {"file": ("export.json", json.dumps(payload), "application/json")}
    import_resp = client.post("/data/import", files=files, follow_redirects=False)
    assert import_resp.status_code in (200, 303)

    session.expire_all()
    restored_ing = session.exec(select(Ingredient).where(Ingredient.name == "りんご")).first()
    restored_menu = session.exec(select(Menu).where(Menu.name == "アップルパイ")).first()
    assert restored_ing is not None
    assert restored_menu is not None
