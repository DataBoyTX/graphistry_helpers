"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Quote Generator"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./quote_generator.db"

    # Security
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Frontend URL (for CORS and redirects)
    frontend_url: str = "http://localhost:5173"

    # Quote Settings
    default_quote_validity_days: int = 30
    default_tax_rate: float = 0.0  # Default tax rate (0%)
    quote_number_prefix: str = "Q"
    order_number_prefix: str = "O"

    @property
    def google_scopes(self) -> list[str]:
        """Google OAuth scopes required for the application."""
        return [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/gmail.compose",
        ]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
