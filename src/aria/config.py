"""Configuration and settings for Aria."""

from pathlib import Path
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and config file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App directories
    app_name: str = "Aria"
    app_version: str = "0.1.0"
    data_dir: Path = Path.home() / ".aria"
    vault_dir: Path = Path.home() / ".aria" / "vault"
    db_path: Path = Path.home() / ".aria" / "aria.db"

    # API Keys (loaded from environment)
    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None

    # UI Settings
    min_window_width: int = 1024
    min_window_height: int = 768
    default_window_width: int = 1400
    default_window_height: int = 900

    # Vault Settings
    max_file_size_mb: int = 50
    supported_extensions: list[str] = [".pdf", ".txt", ".docx", ".csv", ".xlsx", ".md"]


# Global settings instance
settings: Final[Settings] = Settings()

# Ensure data directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.vault_dir.mkdir(parents=True, exist_ok=True)
