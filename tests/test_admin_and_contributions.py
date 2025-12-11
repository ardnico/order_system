from sqlmodel import Session, select

from app.main import ROOT_PASSWORD, ROOT_EMAIL
from app.models import Household, PointTransaction, User


def test_root_admin_login_and_admin_page(client, session: Session):
    root_user = session.exec(select(User).where(User.email == ROOT_EMAIL)).first()
    assert root_user is not None
    resp = client.post(
        "/login",
        data={
            "email": ROOT_EMAIL,
            "password": ROOT_PASSWORD,
            "household_id": root_user.household_id,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    admin_page = client.get("/admin")
    assert admin_page.status_code == 200
    assert "admin" in admin_page.text.lower()


def test_contribution_points_award_on_menu(client, session: Session):
    # Register and set contribution rate to 1 action = 1pt
    client.post(
        "/register",
        data={
            "display_name": "Chef",
            "email": "chef@example.com",
            "password": "pw",
            "create_household": "1",
            "household_name": "Kitchen",
            "join_code": "kc",
        },
    )
    user = session.exec(select(User).where(User.email == "chef@example.com")).first()
    household = session.get(Household, user.household_id)
    client.post(
        "/settings/language",
        data={
            "language": household.language,
            "theme": household.theme,
            "font": household.font,
            "household_name": household.name,
            "join_code": household.join_code,
            "contribution_rate": 1,
        },
        follow_redirects=False,
    )

    create_resp = client.post(
        "/menus",
        data={
            "name": "Pasta",
            "description": "",
            "ingredient_names": ["Noodle", "Sauce"],
            "ingredient_quantities": ["1", "1"],
            "ingredient_units": ["", ""],
        },
        files={},
        follow_redirects=False,
    )
    assert create_resp.status_code == 303
    session.expire_all()
    tx = session.exec(select(PointTransaction)).first()
    assert tx is not None
    assert tx.amount >= 1
