"""Unit tests for service-layer helpers."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.services import data_loader as data_loader_module
from app.services.data_loader import DataLoader, resolve_dynamic_dates
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

    agreement_directory = tmp_path / "agreement"
    agreement_directory.mkdir()
    (agreement_directory / "USER-001.json").write_text(
        json.dumps({"agreementId": "AGR-001", "status": "ACTIVE"}),
        encoding="utf-8",
    )

    loader = DataLoader(tmp_path)

    payload = loader.load_status_payload("agreement", "USER-001")

    assert payload == {"agreementId": "AGR-001", "status": "ACTIVE"}


def test_data_loader_raises_file_not_found_for_unknown_paths(tmp_path: Path) -> None:
    """The data loader should raise FileNotFoundError when the fixture is missing."""

    loader = DataLoader(tmp_path)

    with pytest.raises(FileNotFoundError, match="No mock data configured for path 'quota'"):
        loader.load_status_payload("quota", "USER-001")


def test_data_loader_rejects_non_object_json_payloads(tmp_path: Path) -> None:
    """The data loader should reject fixtures that are not JSON objects."""

    invalid_directory = tmp_path / "invalid"
    invalid_directory.mkdir()
    (invalid_directory / "USER-001.json").write_text(
        json.dumps(["unexpected", "array"]), encoding="utf-8"
    )

    loader = DataLoader(tmp_path)

    with pytest.raises(ValueError, match="top-level object"):
        loader.load_status_payload("invalid", "USER-001")


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


class _FrozenDateTime(datetime):
    """A ``datetime`` subclass whose ``now`` returns a fixed instant."""

    _frozen = datetime(2026, 6, 11, 9, 30, 0)

    @classmethod
    def now(cls, tz=None) -> datetime:  # type: ignore[override]
        return cls._frozen


@pytest.fixture()
def frozen_now(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Freeze ``datetime.now`` inside the data loader to a known instant."""

    monkeypatch.setattr(data_loader_module, "datetime", _FrozenDateTime)
    return _FrozenDateTime._frozen


def test_resolve_dynamic_dates_adds_days_with_default_format(frozen_now: datetime) -> None:
    """A ``days`` placeholder should resolve to an ISO timestamp shifted by days."""

    assert resolve_dynamic_dates("{{ days:+5 }}") == "2026-06-16T09:30:00Z"


def test_resolve_dynamic_dates_supports_negative_amounts(frozen_now: datetime) -> None:
    """A negative amount should shift the date into the past."""

    assert resolve_dynamic_dates("{{ weeks:-2 }}") == "2026-05-28T09:30:00Z"


def test_resolve_dynamic_dates_defaults_unsigned_amounts_to_addition(frozen_now: datetime) -> None:
    """An amount without a sign should be treated as a positive offset."""

    assert resolve_dynamic_dates("{{ days:3 }}") == "2026-06-14T09:30:00Z"


def test_resolve_dynamic_dates_handles_months_and_years(frozen_now: datetime) -> None:
    """Month and year placeholders should shift the calendar accordingly."""

    assert resolve_dynamic_dates("{{ months:-1 }}") == "2026-05-11T09:30:00Z"
    assert resolve_dynamic_dates("{{ years:+1 }}") == "2027-06-11T09:30:00Z"


def test_resolve_dynamic_dates_clamps_day_to_month_length(monkeypatch: pytest.MonkeyPatch) -> None:
    """Adding a month from the 31st should clamp to the shorter month's last day."""

    class _Jan31(datetime):
        @classmethod
        def now(cls, tz=None) -> datetime:  # type: ignore[override]
            return datetime(2026, 1, 31, 0, 0, 0)

    monkeypatch.setattr(data_loader_module, "datetime", _Jan31)

    assert resolve_dynamic_dates("{{ months:+1 | %Y-%m-%d }}") == "2026-02-28"


def test_resolve_dynamic_dates_applies_custom_format(frozen_now: datetime) -> None:
    """An explicit strftime format after a pipe should drive the output."""

    assert resolve_dynamic_dates("{{ months:-1 | %Y-%m-%d }}") == "2026-05-11"
    assert resolve_dynamic_dates("{{ days:+30 | %d/%m/%Y }}") == "11/07/2026"


def test_resolve_dynamic_dates_replaces_placeholder_within_surrounding_text(
    frozen_now: datetime,
) -> None:
    """Placeholders embedded in longer strings should be replaced in place."""

    resolved = resolve_dynamic_dates("vence el {{ days:+5 | %d/%m/%Y }} sin falta")

    assert resolved == "vence el 16/06/2026 sin falta"


def test_resolve_dynamic_dates_walks_nested_structures(frozen_now: datetime) -> None:
    """Placeholders at every level of dicts and lists should be resolved."""

    payload = {
        "nested": {"due": "{{ days:+5 | %Y-%m-%d }}"},
        "items": ["{{ weeks:-1 | %Y-%m-%d }}", {"renewal": "{{ months:+1 | %Y-%m-%d }}"}],
    }

    resolved = resolve_dynamic_dates(payload)

    assert resolved == {
        "nested": {"due": "2026-06-16"},
        "items": ["2026-06-04", {"renewal": "2026-07-11"}],
    }


def test_resolve_dynamic_dates_leaves_non_string_values_untouched(frozen_now: datetime) -> None:
    """Numbers, booleans and ``None`` should pass through unchanged."""

    payload = {"count": 42, "active": True, "missing": None, "ratio": 1.5}

    assert resolve_dynamic_dates(payload) == payload


def test_resolve_dynamic_dates_ignores_unknown_units(frozen_now: datetime) -> None:
    """Strings without a valid placeholder should be returned verbatim."""

    assert resolve_dynamic_dates("{{ centuries:+1 }}") == "{{ centuries:+1 }}"
    assert resolve_dynamic_dates("plain text") == "plain text"
