import os
import datetime as dt
import jwt
from passlib.context import CryptContext
from sqlalchemy import or_

from backend.db import get_session
from backend.models import User

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-prod-please")
JWT_ALG = "HS256"
JWT_TTL_DAYS = 7

_pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def _make_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": dt.datetime.utcnow() + dt.timedelta(days=JWT_TTL_DAYS),
        "iat": dt.datetime.utcnow(),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALG
    )


def signup(username: str,
           email: str,
           password: str) -> str:

    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        raise ValueError("All fields are required.")

    if len(password) < 6:
        raise ValueError(
            "Password must be at least 6 characters."
        )

    with get_session() as s:

        existing = (
            s.query(User)
            .filter(
                or_(
                    User.username == username,
                    User.email == email
                )
            )
            .first()
        )

        if existing:
            raise ValueError(
                "Username or email already taken."
            )

        user = User(
            username=username,
            email=email,
            password_hash=_pwd.hash(password)
        )

        s.add(user)
        s.flush()

        return _make_token(user.id)


def login(username_or_email: str,
          password: str) -> str:

    key = username_or_email.strip()

    with get_session() as s:

        user = (
            s.query(User)
            .filter(
                or_(
                    User.username == key,
                    User.email == key.lower()
                )
            )
            .first()
        )

        if not user:
            raise ValueError("Invalid credentials.")

        if not _pwd.verify(
            password,
            user.password_hash
        ):
            raise ValueError("Invalid credentials.")

        return _make_token(user.id)


def current_user(token):

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG]
        )

        uid = int(payload["sub"])

    except Exception:
        return None

    with get_session() as s:

        user = s.get(User, uid)

        if not user:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }


def logout():
    return True