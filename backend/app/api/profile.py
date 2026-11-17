from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.config import get_db
from app.models import User
from app.schemas.profile import HealthProfileResponse, HealthProfileUpdate
from app.security.dependencies import get_current_user
from app.services.profile_service import (
    ProfilePersistenceConflict,
    get_profile,
    update_profile,
)

router = APIRouter(tags=["health profile"])


@router.get("/profile", response_model=HealthProfileResponse)
def read_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    profile = get_profile(session, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return profile


@router.put("/profile", response_model=HealthProfileResponse)
def write_profile(
    data: HealthProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    try:
        profile = update_profile(session, current_user.id, data)
    except ProfilePersistenceConflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile could not be saved due to a data conflict.",
        ) from None
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return profile
