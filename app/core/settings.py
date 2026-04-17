"""Application settings module."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the application."""

    app_name: str = "Mock API"
    token_expiration_seconds: int = 3600
    default_delay_seconds: int = 60
    data_directory: Path = Path("app/data")

    model_config = SettingsConfigDict(env_prefix="MOCK_API_")


settings = Settings()
