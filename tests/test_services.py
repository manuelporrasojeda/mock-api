"""Unit tests for service-layer helpers."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from app.services.data_loader import DataLoader
from app.services.mock_behavior_service import MockBehaviorService
from app.services.token_service import TokenService


def test_decode_basic_authorization_returns_credentials() -> None:
    """Basic authorization headers should be decoded into client credentials."""

    encoded_credentials = base64.b64encode(b"client-id:client-secret").decode("utf-8")

    credentials = TokenService.decode_basic_authorization(f"Basic {encoded_credentials}")

    assert credentials.client_id == "client-id"
    assert credentials.client_secret == "client-secret"


def test_decode_basic_authorization_rejects_malformed_headers() -> None:
    """Malformed Basic authorization headers should raise a ValueError."""

    with pytest.raises(ValueError, match="Invalid Basic authorization header"):
        TokenService.decode_basic_authorization("Basic malformed")


def test_data_loader_reads_json_objects(tmp_path: Path) -> None:
    """The data loader should return JSON fixtures stored as top-level objects."""

    fixture_directory = tmp_path / "status"
    fixture_directory.mkdir()
    (fixture_directory / "agreement.json").write_text(
        json.dumps({"agreementId": "AGR-001", "status": "ACTIVE"}),
        encoding="utf-8",
    )

    loader = DataLoader(fixture_directory)

    payload = loader.load_status_payload("agreement")

    assert payload == {"agreementId": "AGR-001", "status": "ACTIVE"}


def test_data_loader_raises_file_not_found_for_unknown_paths(tmp_path: Path) -> None:
    """The data loader should raise FileNotFoundError when the fixture is missing."""

    fixture_directory = tmp_path / "status"
    fixture_directory.mkdir()
    loader = DataLoader(fixture_directory)

    with pytest.raises(FileNotFoundError, match="No mock data configured for path 'quota'"):
        loader.load_status_payload("quota")


def test_data_loader_rejects_non_object_json_payloads(tmp_path: Path) -> None:
    """The data loader should reject fixtures that are not JSON objects."""

    fixture_directory = tmp_path / "status"
    fixture_directory.mkdir()
    (fixture_directory / "invalid.json").write_text(json.dumps(["unexpected", "array"]), encoding="utf-8")

    loader = DataLoader(fixture_directory)

    with pytest.raises(ValueError, match="top-level object"):
        loader.load_status_payload("invalid")


def test_mock_behavior_service_returns_error_scenario_for_missing_user() -> None:
    """A configured special user should return the expected upstream error scenario."""

    scenario = MockBehaviorService.get_user_token_scenario("noexistinguser")

    assert scenario is not None
    assert scenario.behavior == "error"
    assert scenario.error is not None
    assert scenario.error.status_code == 500


def test_mock_behavior_service_returns_delay_scenario_for_status_identity() -> None:
    """A configured status identity should resolve to a delay scenario."""

    scenario = MockBehaviorService.get_status_scenario(
        path_name="agreement",
        national_identity_card_nr="slowuser",
        account_id="ACC-001",
    )

    assert scenario is not None
    assert scenario.behavior == "delay"
    assert scenario.delay_seconds is not None
