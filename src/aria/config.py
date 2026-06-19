"""Configuration and settings for Aria."""

from pathlib import Path
from typing import Any, Final

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource


class Settings(BaseSettings):
    """Application settings loaded from TOML, environment variables, and .env."""

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

    # API Keys (loaded from environment or ~/.aria/config.toml)
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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Add ~/.aria/config.toml as a settings source.

        Priority (highest to lowest):
        1. Init kwargs (programmatic overrides)
        2. Environment variables
        3. ~/.aria/config.toml
        4. .env file
        5. Secrets directory
        """
        toml_path = Path.home() / ".aria" / "config.toml"
        # Ensure the config directory exists (safe on repeat calls)
        toml_path.parent.mkdir(parents=True, exist_ok=True)
        toml_source = TomlConfigSettingsSource(settings_cls, toml_file=toml_path)
        return (
            init_settings,
            env_settings,
            toml_source,
            dotenv_settings,
            file_secret_settings,
        )


# Global settings instance
settings: Final[Settings] = Settings()

# Ensure data directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.vault_dir.mkdir(parents=True, exist_ok=True)
