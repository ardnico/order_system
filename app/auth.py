import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlmodel import Session, select

from .db import get_session
from .models import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> Optional[User]:
    user_id = request.session.get("user_id")
    household_id = request.session.get("household_id")
    if not user_id or not household_id:
        return None
    statement = select(User).where(User.id == user_id, User.household_id == household_id)
    result = session.exec(statement).first()
    return result


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=401)
    return user


def login_user(request: Request, user: User):
    request.session["user_id"] = user.id
    request.session["household_id"] = user.household_id
    request.session["csrf_token"] = secrets.token_hex(16)


def logout_user(request: Request):
    request.session.clear()
