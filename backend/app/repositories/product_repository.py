from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Product, ProductIngredient


class ProductRepository:
    @staticmethod
    def list_with_nutrients(
        session: Session,
        *,
        limit: int = 200,
    ) -> list[Product]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        return list(
            session.scalars(
                select(Product)
                .options(
                    selectinload(Product.nutrients),
                    selectinload(Product.ingredients).selectinload(
                        ProductIngredient.ingredient
                    ),
                )
                .order_by(Product.product_name, Product.id)
                .limit(limit)
            ).all()
        )
