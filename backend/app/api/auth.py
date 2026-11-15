from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.config import get_db
from app.models import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, RegisterRequest
from app.schemas.users import UserRead
from app.security.dependencies import get_current_user
from app.security.tokens import create_access_token
from app.services.auth_service import (
    DuplicateEmailError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)


router = APIRouter(tags=["authentication"])


@router.post(
    "/auth/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(data: RegisterRequest, session: Session = Depends(get_db)):
    try:
        return register_user(session, data)
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None


@router.post("/auth/login", response_model=AccessTokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_db)):
    try:
        user = authenticate_user(
            session,
            email=str(data.email),
            password=data.password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    try:
        token, expires_in = create_access_token(user.id)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        ) from error
    return AccessTokenResponse(access_token=token, expires_in=expires_in)


@router.get("/auth/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user
