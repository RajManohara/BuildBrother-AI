from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server-only configuration. No API keys are sent to the browser."""

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str = "sqlite:///./buildbrother.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    demo_mode: bool = True
    app_api_key: str = ""
    ingest_token: str = ""
    github_app_id: str = ""
    github_installation_id: int = 0
    github_private_key: str = ""
    github_repository: str = "RajManohara/BuildBrother-AI"
    github_api_version: str = "2026-03-10"
    collector_interval_seconds: int = Field(default=300, ge=60)
