from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    @staticmethod
    def create(
        session: Session,
        *,
        name: str,
        email: str,
        password_hash: str,
    ) -> User:
        user = User(name=name, email=email, password_hash=password_hash)
        session.add(user)
        session.flush()
        return user

    @staticmethod
    def get_by_id(session: Session, user_id: int) -> User | None:
        return session.get(User, user_id)

    @staticmethod
    def get_by_email(session: Session, email: str) -> User | None:
        normalized_email = email.strip().casefold()
        return session.scalar(
            select(User).where(func.lower(User.email) == normalized_email)
        )
