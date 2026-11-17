"""Environment-backed CORS configuration."""

import os
from collections.abc import Mapping
from urllib.parse import urlsplit

DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)


def load_cors_settings(
    environ: Mapping[str, str] | None = None,
) -> tuple[list[str], bool]:
    environment = os.environ if environ is None else environ
    configured_origins = environment.get("CORS_ALLOWED_ORIGINS")
    if configured_origins is None:
        origins = list(DEFAULT_ALLOWED_ORIGINS)
    else:
        origins = [
            origin.strip()
            for origin in configured_origins.split(",")
            if origin.strip()
        ]
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            port = parsed.port
        except ValueError as error:
            raise ValueError("CORS_ALLOWED_ORIGINS contains an invalid origin.") from error
        if (
            origin != "*"
            and (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or (port is not None and not 1 <= port <= 65535)
            )
        ):
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must contain exact HTTP or HTTPS origins."
            )

    raw_credentials = environment.get("CORS_ALLOW_CREDENTIALS", "true").strip().lower()
    if raw_credentials not in {"true", "false"}:
        raise ValueError("CORS_ALLOW_CREDENTIALS must be true or false.")
    allow_credentials = raw_credentials == "true"

    if allow_credentials and "*" in origins:
        raise ValueError(
            "CORS_ALLOWED_ORIGINS cannot contain '*' when "
            "CORS_ALLOW_CREDENTIALS is true."
        )
    return origins, allow_credentials
