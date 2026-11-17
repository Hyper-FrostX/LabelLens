import pytest
from fastapi.testclient import TestClient

from app.security.cors import DEFAULT_ALLOWED_ORIGINS, load_cors_settings
from app.security.rate_limit import (
    RateLimitPolicy,
    RequestRateLimiter,
    load_rate_limit_policies,
)
from main import app

client = TestClient(app)


def test_rate_limiter_is_scoped_by_client_and_operation():
    limiter = RequestRateLimiter(
        {
            "extract_label": RateLimitPolicy(max_requests=1, window_seconds=10),
            "product_ask": RateLimitPolicy(max_requests=1, window_seconds=10),
        }
    )

    assert limiter.check("extract_label", "client-a", now=100) is None
    assert limiter.check("extract_label", "client-a", now=101) == 9
    assert limiter.check("product_ask", "client-a", now=101) is None
    assert limiter.check("extract_label", "client-b", now=101) is None
    assert limiter.check("extract_label", "client-a", now=110) is None


def test_rate_limit_configuration_uses_defaults_and_accepts_overrides():
    defaults = load_rate_limit_policies({})
    assert defaults["extract_label"] == RateLimitPolicy(10, 60)
    assert defaults["product_ask"] == RateLimitPolicy(20, 60)

    configured = load_rate_limit_policies(
        {
            "EXTRACT_LABEL_RATE_LIMIT_REQUESTS": "3",
            "EXTRACT_LABEL_RATE_LIMIT_WINDOW_SECONDS": "15",
            "PRODUCT_ASK_RATE_LIMIT_REQUESTS": "7",
            "PRODUCT_ASK_RATE_LIMIT_WINDOW_SECONDS": "45",
        }
    )
    assert configured["extract_label"] == RateLimitPolicy(3, 15)
    assert configured["product_ask"] == RateLimitPolicy(7, 45)


@pytest.mark.parametrize(
    "environment",
    [
        {"EXTRACT_LABEL_RATE_LIMIT_REQUESTS": "0"},
        {"PRODUCT_ASK_RATE_LIMIT_WINDOW_SECONDS": "not-a-number"},
    ],
)
def test_rate_limit_configuration_rejects_invalid_values(environment):
    with pytest.raises(ValueError):
        load_rate_limit_policies(environment)


def test_cors_configuration_has_local_defaults_and_accepts_origins():
    assert load_cors_settings({}) == (list(DEFAULT_ALLOWED_ORIGINS), True)
    configured_origins, configured_credentials = load_cors_settings()
    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )
    assert cors_middleware.kwargs["allow_origins"] == configured_origins
    assert cors_middleware.kwargs["allow_credentials"] is configured_credentials
    assert load_cors_settings(
        {
            "CORS_ALLOWED_ORIGINS": "https://app.example, https://admin.example ",
            "CORS_ALLOW_CREDENTIALS": "false",
        }
    ) == (["https://app.example", "https://admin.example"], False)


def test_cors_rejects_wildcard_with_credentials():
    with pytest.raises(ValueError, match="cannot contain"):
        load_cors_settings(
            {
                "CORS_ALLOWED_ORIGINS": "https://app.example, *",
                "CORS_ALLOW_CREDENTIALS": "true",
            }
        )


def test_cors_allows_wildcard_without_credentials():
    assert load_cors_settings(
        {
            "CORS_ALLOWED_ORIGINS": "*",
            "CORS_ALLOW_CREDENTIALS": "false",
        }
    ) == (["*"], False)


@pytest.mark.parametrize(
    "origin",
    [
        "example.com",
        "https://app.example/path",
        "https://app.example?query=1",
        "http://localhost:99999",
    ],
)
def test_cors_rejects_non_origin_values(origin):
    with pytest.raises(ValueError, match="origin"):
        load_cors_settings(
            {
                "CORS_ALLOWED_ORIGINS": origin,
                "CORS_ALLOW_CREDENTIALS": "false",
            }
        )


def test_expensive_api_operations_return_429_per_client_and_operation(
    monkeypatch,
):
    import main
    from app.services import label_ocr

    monkeypatch.setattr(
        main,
        "request_rate_limiter",
        RequestRateLimiter(
            {
                "extract_label": RateLimitPolicy(1, 60),
                "product_ask": RateLimitPolicy(1, 60),
            }
        ),
    )
    monkeypatch.setattr(
        label_ocr,
        "validate_image",
        lambda _: None,
    )
    monkeypatch.setattr(
        label_ocr,
        "extract_image_data",
        lambda _: {
            "ocr_text": "",
            "raw_ocr_text": "",
            "regions": [],
            "fields": [],
            "symbol_detection": {"image_inspected": True},
            "processing": {"original_image_unchanged": True},
            "ocr_quality": {"mean_word_confidence": None},
            "ocr_passes": [],
        },
    )

    first_question = client.post(
        "/analyze/product/ask",
        json={"question": "What does this label say?"},
    )
    second_question = client.post(
        "/analyze/product/ask",
        json={"question": "Is it high in sodium?"},
    )
    assert first_question.status_code == 200
    assert second_question.status_code == 429
    assert second_question.json()["detail"] == "Rate limit exceeded. Try again later."
    assert second_question.headers["retry-after"].isdigit()

    image = client.post(
        "/extract/label",
        files={"file": ("label.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert image.status_code == 200
    image_again = client.post(
        "/extract/label",
        files={"file": ("label.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert image_again.status_code == 429
    assert image_again.headers["retry-after"].isdigit()
