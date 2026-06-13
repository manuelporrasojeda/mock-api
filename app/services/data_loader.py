"""Data loading helpers for JSON-backed mock responses."""

from __future__ import annotations

import calendar
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Matches placeholders such as ``{{ days:+5 }}`` or ``{{ months:-1 | %Y-%m-%d }}``.
# Groups: (unit, signed amount, optional strftime format).
_PLACEHOLDER_PATTERN = re.compile(
    r"\{\{\s*"
    r"(years|months|weeks|days|hours|minutes|seconds)"
    r"\s*:\s*([+-]?\d+)\s*"
    r"(?:\|\s*(.+?)\s*)?"
    r"\}\}"
)

# Default output when a placeholder does not specify its own format.
_DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _add_months(base: datetime, months: int) -> datetime:
    """Return ``base`` shifted by ``months``, clamping the day to month length."""

    month_index = base.month - 1 + months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return base.replace(year=year, month=month, day=day)


def _shift_now(unit: str, amount: int) -> datetime:
    """Return the current time shifted by ``amount`` of the given ``unit``."""

    now = datetime.now()
    if unit == "years":
        return _add_months(now, amount * 12)
    if unit == "months":
        return _add_months(now, amount)
    if unit == "weeks":
        return now + timedelta(weeks=amount)
    if unit == "days":
        return now + timedelta(days=amount)
    if unit == "hours":
        return now + timedelta(hours=amount)
    if unit == "minutes":
        return now + timedelta(minutes=amount)
    if unit == "seconds":
        return now + timedelta(seconds=amount)
    raise ValueError(f"Unsupported date unit '{unit}'.")


def _replace_placeholders(value: str) -> str:
    """Replace every date placeholder found inside ``value``."""

    def _substitute(match: re.Match[str]) -> str:
        unit, amount, date_format = match.group(1), int(match.group(2)), match.group(3)
        shifted = _shift_now(unit, amount)
        return shifted.strftime(date_format or _DEFAULT_DATE_FORMAT)

    return _PLACEHOLDER_PATTERN.sub(_substitute, value)


def resolve_dynamic_dates(value: Any) -> Any:
    """Recursively resolve date placeholders within any JSON-like structure.

    Walks dictionaries, lists and strings at every level. Strings containing a
    placeholder such as ``{{ days:+5 }}`` are rewritten with a date relative to
    now. Supported units are ``years``, ``months``, ``weeks``, ``days``,
    ``hours``, ``minutes`` and ``seconds``, each with a ``+`` or ``-`` amount.
    An optional ``strftime`` format may follow a pipe, e.g.
    ``{{ months:-1 | %Y-%m-%d }}``.
    """

    if isinstance(value, dict):
        return {key: resolve_dynamic_dates(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_dynamic_dates(item) for item in value]
    if isinstance(value, str):
        return _replace_placeholders(value)
    return value


class DataLoader:
    """Loads JSON fixtures for the status endpoints."""

    def __init__(self, data_directory: Path) -> None:
        """Create a new loader bound to a fixture directory."""

        self._data_directory = data_directory

    def load_status_payload(self, path_name: str, user_id: str) -> dict[str, Any]:
        """Load a JSON payload based on the path segment.

        Args:
            path_name: The first URL path segment, such as ``agreement`` or ``quota``.
            user_id: The ID of the user for whom to load the data.

        Raises:
            FileNotFoundError: If the mapped JSON fixture does not exist.
            ValueError: If the file exists but does not contain a JSON object.
        """
        if '/' in path_name:
            path_name = path_name.split('/')[0]
        file_path = self._data_directory / f"{path_name}/{user_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"No mock data configured for path '{path_name}' and user '{user_id}'.")

        with file_path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        if not isinstance(payload, dict) or isinstance(payload, list):
            raise ValueError("The JSON fixture must contain a top-level object.")

        return resolve_dynamic_dates(payload)
