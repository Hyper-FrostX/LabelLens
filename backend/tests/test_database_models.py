from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Allergen,
    ExpertiseLevel,
    ExtractedLabel,
    HealthCondition,
    HealthProfile,
    Ingredient,
    NutrientBasis,
    Product,
    ProductIngredient,
    ProductNutrient,
    Scan,
    User,
    UserAllergen,
    UserHealthCondition,
)
from app.repositories import ScanRepository, UserRepository
from app.schemas import (
    AnalysisFindingCreate,
    AnalysisReportCreate,
    ExtractedLabelCreate,
    ScanCreate,
    ScanRead,
    UserRead,
)


def _create_user(db_session, *, email="person@example.invalid"):
    return UserRepository.create(
        db_session,
        name="Test User",
        email=email,
        password_hash="test-hash",
    )


def test_user_profile_conditions_and_allergens_relationships(db_session):
    user = _create_user(db_session)
    condition = HealthCondition(name="Diabetes")
    allergen = Allergen(name="Peanut", category="nut")
    user.health_profile = HealthProfile(expertise_level=ExpertiseLevel.EXPERT)
    user.health_condition_selections.append(
        UserHealthCondition(condition=condition)
    )
    user.allergen_selections.extend(
        [
            UserAllergen(allergen=allergen),
            UserAllergen(custom_allergen_name="Mustard"),
        ]
    )
    db_session.commit()
    db_session.expire_all()

    saved_user = UserRepository.get_by_id(db_session, user.id)

    assert saved_user is not None
    assert saved_user.health_profile.expertise_level is ExpertiseLevel.EXPERT
    assert saved_user.health_condition_selections[0].condition.name == "Diabetes"
    catalog_selection = next(
        selection
        for selection in saved_user.allergen_selections
        if selection.allergen_id is not None
    )
    custom_selection = next(
        selection
        for selection in saved_user.allergen_selections
        if selection.allergen_id is None
    )
    assert catalog_selection.allergen.name == "Peanut"
    assert custom_selection.custom_allergen_name == "Mustard"
    assert "password_hash" not in UserRead.model_validate(saved_user).model_dump()


def test_product_ingredients_and_nutrients_relationships(db_session):
    product = Product(product_name="Oat Crunch", barcode="0123456789012")
    oats = Ingredient(
        canonical_name="Oats",
        description="Whole grain",
        ingredient_type="food",
    )
    salt = Ingredient(
        canonical_name="Salt",
        description=None,
        ingredient_type="mineral",
    )
    product.ingredients.extend(
        [
            ProductIngredient(
                ingredient=oats,
                ingredient_order=0,
                original_label_text="whole oats",
            ),
            ProductIngredient(
                ingredient=salt,
                ingredient_order=1,
                original_label_text="salt",
            ),
        ]
    )
    product.nutrients.append(
        ProductNutrient(
            nutrient_name="sodium",
            amount=Decimal("120.5000"),
            unit="mg",
            basis=NutrientBasis.PER_100G,
        )
    )
    db_session.add(product)
    db_session.commit()
    db_session.expire_all()

    saved_product = db_session.get(Product, product.id)

    assert [item.ingredient_order for item in saved_product.ingredients] == [0, 1]
    assert saved_product.ingredients[0].ingredient.canonical_name == "Oats"
    assert saved_product.ingredients[0].original_label_text == "whole oats"
    assert saved_product.nutrients[0].amount == Decimal("120.5000")
    assert saved_product.nutrients[0].basis is NutrientBasis.PER_100G


def test_scan_extracted_label_reports_and_findings_relationships(db_session):
    user = _create_user(db_session)
    scan = ScanRepository.create_for_user(
        db_session,
        user_id=user.id,
        data=ScanCreate(uploaded_image_path="uploads/label.png"),
    )
    extracted_label = ScanRepository.save_extracted_label(
        db_session,
        scan_id=scan.id,
        user_id=user.id,
        data=ExtractedLabelCreate(
            extracted_data={"basis": "per_100g"},
            ocr_text="Nutrition label text",
            extraction_version="label-parser-v1",
        ),
    )
    report = ScanRepository.add_analysis_report(
        db_session,
        scan_id=scan.id,
        user_id=user.id,
        data=AnalysisReportCreate(
            health_score=Decimal("76.50"),
            analysis_data={"status": "available"},
            scoring_version="score-v1",
            findings=[
                AnalysisFindingCreate(
                    finding_type="nutrient",
                    severity="moderate",
                    title="Sodium",
                    description="Sodium amount requires review.",
                    evidence_reference=None,
                )
            ],
        ),
    )
    second_report = ScanRepository.add_analysis_report(
        db_session,
        scan_id=scan.id,
        user_id=user.id,
        data=AnalysisReportCreate(
            health_score=None,
            analysis_data={"status": "needs_review"},
            scoring_version="score-v2",
        ),
    )
    db_session.commit()
    db_session.expire_all()

    saved_scan = db_session.get(Scan, scan.id)
    assert saved_scan.user_id == user.id
    assert saved_scan.extracted_label.id == extracted_label.id
    assert saved_scan.extracted_label.ocr_text == "Nutrition label text"
    assert {item.id for item in saved_scan.analysis_reports} == {
        report.id,
        second_report.id,
    }
    saved_report = next(
        item for item in saved_scan.analysis_reports if item.id == report.id
    )
    assert saved_report.health_score == Decimal("76.50")
    assert saved_report.findings[0].title == "Sodium"
    assert ScanRead.model_validate(saved_scan).extracted_label.ocr_text == (
        "Nutrition label text"
    )

    db_session.add(
        ExtractedLabel(
            scan_id=scan.id,
            extracted_data={},
            ocr_text="duplicate",
            extraction_version="v2",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_scan_repository_scopes_reads_and_saves_to_user(db_session):
    user = _create_user(db_session)
    other_user = _create_user(db_session, email="other@example.invalid")
    scan = ScanRepository.create_for_user(
        db_session,
        user_id=user.id,
        data=ScanCreate(),
    )
    db_session.commit()

    assert ScanRepository.get_for_user(
        db_session,
        scan_id=scan.id,
        user_id=user.id,
    ).id == scan.id
    assert (
        ScanRepository.get_for_user(
            db_session,
            scan_id=scan.id,
            user_id=other_user.id,
        )
        is None
    )
    assert ScanRepository.list_for_user(db_session, user_id=other_user.id) == []
    with pytest.raises(LookupError, match="not found for this user"):
        ScanRepository.save_extracted_label(
            db_session,
            scan_id=scan.id,
            user_id=other_user.id,
            data=ExtractedLabelCreate(
                extracted_data={},
                ocr_text="",
                extraction_version="v1",
            ),
        )


def test_scan_repository_rejects_anonymous_scan_creation(db_session):
    with pytest.raises(ValueError, match="authenticated user id"):
        ScanRepository.create_for_user(
            db_session,
            user_id=None,
            data=ScanCreate(),
        )


def test_unique_constraints_for_users_profiles_barcodes_and_nutrients(db_session):
    user = _create_user(db_session)
    db_session.commit()
    db_session.add(User(name="Duplicate", email=user.email, password_hash="hash"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    user = UserRepository.get_by_email(db_session, user.email)
    user.health_profile = HealthProfile()
    db_session.commit()
    db_session.add(HealthProfile(user_id=user.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    first = Product(product_name="First", barcode="same-barcode")
    second = Product(product_name="Second", barcode="same-barcode")
    db_session.add_all([first, second])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    product = Product(product_name="Unique nutrients")
    product.nutrients.extend(
        [
            ProductNutrient(
                nutrient_name="sugar",
                amount=Decimal("1"),
                unit="g",
                basis=NutrientBasis.PER_100G,
            ),
            ProductNutrient(
                nutrient_name="sugar",
                amount=Decimal("2"),
                unit="g",
                basis=NutrientBasis.PER_100G,
            ),
        ]
    )
    db_session.add(product)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_keys_and_custom_allergen_constraint_are_enforced(db_session):
    db_session.add(Scan(user_id=999, scan_status="uploaded"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    user = _create_user(db_session)
    db_session.add(UserAllergen(user_id=user.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
