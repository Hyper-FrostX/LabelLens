import secrets
from functools import lru_cache

from pwdlib import PasswordHash
from pwdlib.exceptions import HashVerificationError, UnknownHashError


_password_hash = PasswordHash.recommended()


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return _password_hash.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    if stored_hash is None:
        _password_hash.verify(password, _dummy_password_hash())
        return False
    try:
        return _password_hash.verify(password, stored_hash)
    except (HashVerificationError, UnknownHashError):
        return False
