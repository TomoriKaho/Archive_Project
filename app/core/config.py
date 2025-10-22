"""Application configuration managed via environment variables."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the FastAPI service."""

    secret_key: str = Field(
        default="change-me", description="Secret key used for signing JWT access tokens."
    )
    algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(
        default=60, description="JWT access token expiry time in minutes."
    )

    model_config = SettingsConfigDict(
        env_prefix="", env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
