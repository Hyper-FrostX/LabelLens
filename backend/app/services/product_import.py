from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Product, ProductNutrient
from app.schemas.catalog import ProductImportInput


class ProductImportConflict(Exception):
    """Raised when source identity or barcode matches conflicting catalog rows."""


@dataclass(frozen=True)
class ProductImportResult:
    product: Product
    status: str


def import_product_record(
    session: Session,
    data: ProductImportInput,
) -> ProductImportResult:
    """Persist a provider-supplied record while retaining source and license metadata."""
    source_match = session.scalar(
        select(Product).where(
            Product.source_name == data.source_name,
            Product.source_product_id == data.source_product_id,
        )
    )
    barcode_match = (
        session.scalar(select(Product).where(Product.barcode == data.barcode))
        if data.barcode
        else None
    )
    brand_condition = (
        func.lower(Product.brand) == data.brand.casefold()
        if data.brand
        else Product.brand.is_(None)
    )
    name_match = session.scalar(
        select(Product).where(
            func.lower(Product.product_name) == data.product_name.casefold(),
            brand_condition,
            Product.category == data.category,
        )
    )
    if (
        name_match is not None
        and (source_match is None or name_match.id != source_match.id)
        and (barcode_match is None or name_match.id != barcode_match.id)
    ):
        raise ProductImportConflict(
            "A product with the same name and brand exists without a matching source identity; review before importing."
        )
    if (
        source_match is not None
        and barcode_match is not None
        and source_match.id != barcode_match.id
    ):
        raise ProductImportConflict(
            "Source identity and barcode refer to different catalog products."
        )
    product = source_match or barcode_match
    if product is not None and (
        product.source_name != data.source_name
        or product.source_product_id != data.source_product_id
    ):
        raise ProductImportConflict(
            "The barcode already belongs to a different source record; review before merging."
        )
    status = "UPDATED" if product is not None else "CREATED"
    if product is None:
        product = Product(
            product_name=data.product_name,
            source_name=data.source_name,
            source_product_id=data.source_product_id,
        )
        session.add(product)

    product.product_name = data.product_name
    product.brand = data.brand
    product.barcode = data.barcode
    product.category = data.category
    product.image_url = str(data.image_url) if data.image_url else None
    product.serving_size_text = data.serving_size_text
    product.ingredients_text = data.ingredients_text
    product.declared_allergens = data.declared_allergens
    product.may_contain = data.may_contain
    product.source_name = data.source_name
    product.source_product_id = data.source_product_id
    product.source_url = str(data.source_url)
    product.source_license = data.source_license
    product.source_updated_at = data.source_updated_at
    session.flush()

    session.execute(
        delete(ProductNutrient).where(
            ProductNutrient.product_id == product.id
        )
    )
    session.flush()
    session.expire(product, ["nutrients"])
    product.nutrients.extend(
        ProductNutrient(
            nutrient_name=item.nutrient_name,
            amount=item.amount,
            unit=item.unit,
            basis=item.basis,
        )
        for item in data.nutrients
    )
    session.flush()
    return ProductImportResult(product=product, status=status)
