import json

from app.database.config import get_session_factory
from app.repositories.ingredient_knowledge_repository import (
    IngredientKnowledgeRepository,
)


def main() -> None:
    with get_session_factory()() as session:
        counts = IngredientKnowledgeRepository.seed_curated_data(session)
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
