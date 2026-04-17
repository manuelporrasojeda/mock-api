"""Token creation helpers for the mock API."""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class BasicCredentials:
    """Decoded credentials extracted from an HTTP Basic Authorization header."""

    client_id: str
    client_secret: str


class TokenService:
    """Provides token creation and header decoding helpers."""

    @staticmethod
    def decode_basic_authorization(authorization_header: str) -> BasicCredentials:
        """Decode a Basic authorization header into client credentials.

        Raises:
            ValueError: If the header is missing, malformed, or cannot be decoded.
        """

        if not authorization_header.startswith("Basic "):
            raise ValueError("Authorization header must use the Basic scheme.")

        encoded_value = authorization_header.split(" ", 1)[1].strip()

        try:
            decoded = base64.b64decode(encoded_value).decode("utf-8")
            client_id, client_secret = decoded.split(":", 1)
        except Exception as exc:
            raise ValueError("Invalid Basic authorization header.") from exc

        if not client_id or not client_secret:
            raise ValueError("Both client_id and client_secret are required.")

        return BasicCredentials(client_id=client_id, client_secret=client_secret)

    @staticmethod
    def generate_system_token() -> str:
        """Generate a mock system access token."""

        return f"sys_{secrets.token_urlsafe(32)}"

    @staticmethod
    def generate_refresh_token() -> str:
        """Generate a mock refresh token."""

        return f"ref_{secrets.token_urlsafe(32)}"

    @staticmethod
    def generate_user_token(user_id: str) -> str:
        """Generate a mock user token linked to a specific user identifier."""

        safe_user_id = user_id.replace(" ", "_")
        return f"usr_{safe_user_id}_{secrets.token_urlsafe(24)}"
