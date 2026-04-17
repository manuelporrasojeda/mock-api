"""Data loading helpers for JSON-backed mock responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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

        if not isinstance(payload, dict):
            raise ValueError("The JSON fixture must contain a top-level object.")

        return payload
