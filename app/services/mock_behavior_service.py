"""Centralized mocked behaviors for special testing scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.core.settings import settings

BehaviorType = Literal["error", "delay"]


@dataclass(frozen=True)
class MockErrorScenario:
    """Describe a mocked upstream error response."""

    status_code: int
    error: str
    message: str
    path: str

    def to_payload(self) -> dict[str, Any]:
        """Serialize the scenario into the expected upstream payload shape."""

        timestamp = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        return {
            "timestamp": timestamp,
            "status": self.status_code,
            "error": self.error,
            "message": self.message,
            "path": self.path,
        }


@dataclass(frozen=True)
class MockScenario:
    """Describe a mocked behavior attached to a request identity."""

    behavior: BehaviorType
    delay_seconds: int | None = None
    error: MockErrorScenario | None = None


class MockBehaviorService:
    """Resolve special mocked behaviors for token and status endpoints."""

    _USER_TOKEN_SCENARIOS: dict[str, MockScenario] = {
        "noexistinguser": MockScenario(
            behavior="error",
            error=MockErrorScenario(
                status_code=500,
                error="Internal Server Error",
                message="No message available",
                path="/customtokensfa/oamclientes/token",
            ),
        ),
        "slowuser": MockScenario(
            behavior="delay",
            delay_seconds=settings.default_delay_seconds,
        ),
    }

    _STATUS_SCENARIOS_BY_IDENTITY: dict[str, MockScenario] = {
        "slowuser": MockScenario(
            behavior="delay",
            delay_seconds=settings.default_delay_seconds,
        ),
    }

    @classmethod
    def get_user_token_scenario(cls, user_id: str) -> MockScenario | None:
        """Return the special scenario configured for a user-token request."""

        return cls._USER_TOKEN_SCENARIOS.get(user_id)

    @classmethod
    def get_status_scenario(
        cls,
        path_name: str,
        national_identity_card_nr: str,
        account_id: str,
    ) -> MockScenario | None:
        """Return the special scenario configured for a status request.

        The current mock resolves behaviors by identity first and keeps the
        method signature open for future path-specific rules.
        """

        _ = path_name, account_id
        return cls._STATUS_SCENARIOS_BY_IDENTITY.get(national_identity_card_nr)
