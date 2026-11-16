"""Environment configuration for third-party platform API credentials."""

import os
from functools import lru_cache
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables via pydantic-settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 4000
    http_timeout_seconds: float = 15.0

    # 1. Telegraph Publishing Portal (Optional — auto-provisions token if blank)
    # Docs: https://telegra.ph/api
    telegraph_access_token: str = ""
    telegraph_author_name: str = "Automated Multi-Platform Poster"

    # 2. GitHub Gist API (Personal Access Token with 'gist' scope)
    # Docs: https://docs.github.com/en/rest/gists/gists
    github_token: str = ""

    # 3. Dev.to / Forem API
    # Docs: https://developers.forem.com/api/v1
    devto_api_key: str = ""

    # 4. Bluesky AT Protocol API
    # Docs: https://bsky.network/docs/bluesky-api/creating-a-post/
    bluesky_service_url: str = "https://bsky.social"
    bluesky_handle: str = ""
    bluesky_app_password: str = ""

    # 5. Mastodon REST API
    # Docs: https://docs.joinmastodon.org/methods/statuses/
    mastodon_instance_url: str = "https://mastodon.social"
    mastodon_access_token: str = ""

    # 6. Groq LLM Platform API
    # Docs: https://console.groq.com/docs/api-reference
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    @field_validator("bluesky_service_url", "mastodon_instance_url", mode="before")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.strip().rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (re-reads .env on first call)."""
    return Settings()
