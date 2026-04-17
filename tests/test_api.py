"""Integration tests for the mock API endpoints."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / "app" / "data" / "tests"


def build_basic_authorization(client_id: str = "demo", client_secret: str = "demo") -> str:
    """Build a valid HTTP Basic authorization header value."""

    raw_credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(raw_credentials.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded_credentials}"


def build_system_token_headers() -> dict[str, str]:
    """Build the required headers for the systemic token endpoint."""

    return {
        "Authorization": build_basic_authorization(),
        "oam": "MDAz",
        "app-key": "demo-app",
    }


def build_system_token_form() -> dict[str, str]:
    """Build the expected form body for the systemic token endpoint."""

    return {
        "grant_type": "password",
        "username": "SVC_AGVIRTUAL",
        "password": "Vivo@2025",
        "scope": "ServiceAccount.Profile",
    }


def build_status_params(national_identity_card_nr: str = "agreement") -> dict[str, str]:
    """Build the expected query parameters for the status endpoint."""

    return {
        "accountId": "ACC-001",
        "newFieldsInd": "true",
        "nationalIdentityCardNr": national_identity_card_nr,
    }


def test_healthcheck_returns_ok(client: TestClient) -> None:
    """The health endpoint should report the API as healthy."""

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system_token_endpoint_returns_expected_shape(client: TestClient) -> None:
    """The system token endpoint should return the expected token payload."""

    response = client.post(
        "/oauth2/v1/tokens",
        headers=build_system_token_headers(),
        data=build_system_token_form(),
    )

    body = response.json()

    assert response.status_code == 200
    assert body["expires_in"] == 3600
    assert body["token_type"] == "Bearer"
    assert body["access_token"].startswith("sys_")
    assert body["refresh_token"].startswith("ref_")


def test_system_token_endpoint_rejects_non_basic_authorization(client: TestClient) -> None:
    """The system token endpoint should reject non-Basic authorization headers."""

    headers = build_system_token_headers()
    headers["Authorization"] = "Bearer unexpected"

    response = client.post(
        "/oauth2/v1/tokens",
        headers=headers,
        data=build_system_token_form(),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Authorization header must use the Basic scheme."}


def test_system_token_endpoint_rejects_invalid_basic_payload(client: TestClient) -> None:
    """The system token endpoint should reject malformed Basic credentials."""

    headers = build_system_token_headers()
    headers["Authorization"] = "Basic not-a-valid-base64-value"

    response = client.post(
        "/oauth2/v1/tokens",
        headers=headers,
        data=build_system_token_form(),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Basic authorization header."}


def test_system_token_endpoint_rejects_invalid_grant_type(client: TestClient) -> None:
    """The system token endpoint should reject unsupported grant types."""

    form_data = build_system_token_form()
    form_data["grant_type"] = "client_credentials"

    response = client.post(
        "/oauth2/v1/tokens",
        headers=build_system_token_headers(),
        data=form_data,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "grant_type must be 'password'."}


def test_user_token_endpoint_returns_token(client: TestClient) -> None:
    """The user token endpoint should return a user-specific token."""

    response = client.post(
        "/customTokenOamCustomerUser/v1/token",
        headers={"Authorization": "sys_mock_token"},
        json={"userid": "12345678A"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["access_token"].startswith("usr_12345678A_")


def test_user_token_endpoint_returns_mocked_upstream_error_for_special_user(client: TestClient) -> None:
    """A configured special user should return the mocked upstream error payload."""

    response = client.post(
        "/customTokenOamCustomerUser/v1/token",
        headers={"Authorization": "sys_mock_token"},
        json={"userid": "noexistinguser"},
    )

    body = response.json()

    assert response.status_code == 500
    assert body["status"] == 500
    assert body["error"] == "Internal Server Error"
    assert body["message"] == "No message available"
    assert body["path"] == "/customtokensfa/oamclientes/token"
    assert "timestamp" in body




def test_user_token_endpoint_applies_delay_for_slow_user(client: TestClient, monkeypatch) -> None:
    """A configured slow user should trigger the async delay branch."""

    observed: dict[str, float] = {}

    async def fake_sleep(seconds: float) -> None:
        observed["seconds"] = seconds

    monkeypatch.setattr("app.api.routes.asyncio.sleep", fake_sleep)

    response = client.post(
        "/customTokenOamCustomerUser/v1/token",
        headers={"Authorization": "sys_mock_token"},
        json={"userid": "slowuser"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"].startswith("usr_slowuser_")
    assert observed == {"seconds": 60}


def test_user_token_endpoint_rejects_blank_authorization(client: TestClient) -> None:
    """The user token endpoint should reject blank authorization headers."""

    response = client.post(
        "/customTokenOamCustomerUser/v1/token",
        headers={"Authorization": "   "},
        json={"userid": "12345678A"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The Authorization header is required."}


def test_status_endpoint_loads_fixture_data(client: TestClient) -> None:
    """The status endpoint should return the JSON payload stored on disk."""

    expected_payload = json.loads((FIXTURE_DIRECTORY / "agreement.json").read_text(encoding="utf-8"))

    response = client.get(
        "/agreement/v5/status",
        headers={"Authorization": "Bearer user_token"},
        params=build_status_params(),
    )

    assert response.status_code == 200
    assert response.json() == expected_payload


def test_status_endpoint_rejects_non_bearer_authorization(client: TestClient) -> None:
    """The status endpoint should reject authorization headers without the Bearer scheme."""

    response = client.get(
        "/agreement/v5/status",
        headers={"Authorization": "user_token"},
        params=build_status_params(),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Authorization header must use the Bearer scheme."}




def test_status_endpoint_applies_delay_for_special_identity(client: TestClient, monkeypatch) -> None:
    """A configured identity should trigger the async delay branch before returning data."""

    observed: dict[str, float] = {}

    async def fake_sleep(seconds: float) -> None:
        observed["seconds"] = seconds

    monkeypatch.setattr("app.api.routes.asyncio.sleep", fake_sleep)

    response = client.get(
        "/agreement/v5/status",
        headers={"Authorization": "Bearer user_token"},
        params=build_status_params(national_identity_card_nr="slowuser"),
    )

    assert response.status_code == 200
    assert response.json()["agreementId"] == "AGR-001"
    assert observed == {"seconds": 60}


def test_status_endpoint_returns_not_found_for_unknown_path(client: TestClient) -> None:
    """The status endpoint should return 404 when no fixture exists for the requested path."""

    response = client.get(
        "/unknown/v5/status",
        headers={"Authorization": "Bearer user_token"},
        params=build_status_params(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No mock data configured for path 'unknown'."}
