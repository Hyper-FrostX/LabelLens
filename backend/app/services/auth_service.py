from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import ExpertiseLevel, HealthProfile, User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest
from app.security.passwords import hash_password, verify_password


class DuplicateEmailError(Exception):
    """Raised when an account already exists for the submitted email."""


class InvalidCredentialsError(Exception):
    """Raised when the submitted login credentials are invalid."""


def register_user(session: Session, data: RegisterRequest) -> User:
    if UserRepository.get_by_email(session, str(data.email)) is not None:
        raise DuplicateEmailError
    try:
        user = UserRepository.create(
            session,
            name=data.name,
            email=str(data.email),
            password_hash=hash_password(data.password),
        )
        user.health_profile = HealthProfile(
            expertise_level=ExpertiseLevel.BEGINNER
        )
        session.commit()
        session.refresh(user)
        return user
    except IntegrityError as error:
        session.rollback()
        raise DuplicateEmailError from error
    except SQLAlchemyError:
        session.rollback()
        raise


def authenticate_user(
    session: Session,
    *,
    email: str,
    password: str,
) -> User:
    user = UserRepository.get_by_email(session, email)
    password_matches = verify_password(
        password,
        user.password_hash if user is not None else None,
    )
    if user is None or not password_matches:
        raise InvalidCredentialsError
    return user
