"""Process-local sliding-window limits for expensive API operations."""

import math
import os
import threading
import time
from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitPolicy:
    max_requests: int
    window_seconds: int

    def __post_init__(self):
        if self.max_requests < 1 or self.window_seconds < 1:
            raise ValueError("Rate limits must have positive request and window values.")


DEFAULT_RATE_LIMIT_POLICIES = {
    "extract_label": RateLimitPolicy(max_requests=10, window_seconds=60),
    "product_ask": RateLimitPolicy(max_requests=20, window_seconds=60),
}


def _read_positive_int(
    environment: Mapping[str, str],
    name: str,
    default: int,
) -> int:
    raw_value = environment.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer.") from error
    if value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def load_rate_limit_policies(
    environ: Mapping[str, str] | None = None,
) -> dict[str, RateLimitPolicy]:
    environment = os.environ if environ is None else environ
    return {
        "extract_label": RateLimitPolicy(
            max_requests=_read_positive_int(
                environment,
                "EXTRACT_LABEL_RATE_LIMIT_REQUESTS",
                DEFAULT_RATE_LIMIT_POLICIES["extract_label"].max_requests,
            ),
            window_seconds=_read_positive_int(
                environment,
                "EXTRACT_LABEL_RATE_LIMIT_WINDOW_SECONDS",
                DEFAULT_RATE_LIMIT_POLICIES["extract_label"].window_seconds,
            ),
        ),
        "product_ask": RateLimitPolicy(
            max_requests=_read_positive_int(
                environment,
                "PRODUCT_ASK_RATE_LIMIT_REQUESTS",
                DEFAULT_RATE_LIMIT_POLICIES["product_ask"].max_requests,
            ),
            window_seconds=_read_positive_int(
                environment,
                "PRODUCT_ASK_RATE_LIMIT_WINDOW_SECONDS",
                DEFAULT_RATE_LIMIT_POLICIES["product_ask"].window_seconds,
            ),
        ),
    }


class RequestRateLimiter:
    """Track operation requests per client in this Python process only."""

    def __init__(self, policies: Mapping[str, RateLimitPolicy]):
        self._policies = dict(policies)
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(
        self,
        operation: str,
        client: str,
        *,
        now: float | None = None,
    ) -> int | None:
        """Record an allowed request, or return the whole-second retry delay."""
        policy = self._policies[operation]
        current_time = time.monotonic() if now is None else now
        key = (operation, client)
        with self._lock:
            for existing_key, timestamps in list(self._events.items()):
                active_policy = self._policies[existing_key[0]]
                cutoff = current_time - active_policy.window_seconds
                while timestamps and timestamps[0] <= cutoff:
                    timestamps.popleft()
                if not timestamps:
                    del self._events[existing_key]

            timestamps = self._events[key]
            if len(timestamps) >= policy.max_requests:
                retry_after = timestamps[0] + policy.window_seconds - current_time
                return max(1, math.ceil(retry_after))
            timestamps.append(current_time)
            return None
