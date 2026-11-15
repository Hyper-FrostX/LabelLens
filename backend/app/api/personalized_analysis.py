from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.config import get_db
from app.models import User
from app.repositories.ingredient_knowledge_repository import IngredientKnowledgeRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.personalized_analysis import PersonalizedAnalysisInput
from app.security.dependencies import get_current_user
from app.services.personalized_analysis import analyze_personalized_label


router = APIRouter(tags=["personalized analysis"])


@router.post("/analyze/personalized")
def personalized_analysis_endpoint(
    data: PersonalizedAnalysisInput,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    profile_owner = ProfileRepository.get_for_user(session, current_user.id)
    if profile_owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found.",
        )
    knowledge_records = IngredientKnowledgeRepository.load_catalog(session)
    return analyze_personalized_label(
        profile_owner,
        data,
        knowledge_records=knowledge_records,
    )
