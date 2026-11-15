import os
from datetime import datetime, timedelta, timezone

import jwt


JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_jwt_secret_key() -> str:
    secret_key = os.environ.get("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be configured.")
    if len(secret_key.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes.")
    return secret_key


def get_access_token_expire_minutes() -> int:
    value = os.environ.get(
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    try:
        minutes = int(value)
    except ValueError as error:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer."
        ) from error
    if minutes <= 0:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer."
        )
    return minutes


def create_access_token(subject: int) -> tuple[str, int]:
    expires_in = get_access_token_expire_minutes() * 60
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(subject),
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        get_jwt_secret_key(),
        algorithm=JWT_ALGORITHM,
    )
    return token, expires_in


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        get_jwt_secret_key(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub", "token_type"]},
    )
    if payload.get("token_type") != "access":
        raise jwt.InvalidTokenError("Invalid token type.")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise jwt.InvalidTokenError("Invalid token subject.")
    user_id = int(subject)
    if user_id <= 0:
        raise jwt.InvalidTokenError("Invalid token subject.")
    return user_id
