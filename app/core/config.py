"""
Central app configuration.
All modules pull settings from here — never read os.environ directly elsewhere.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str

    # Claude API
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # External data sources
    newsapi_key: str = ""
    eia_api_key: str = ""
    guardian_api_key: str = ""

    # App
    env: str = "development"
    cors_origins: str = "http://localhost:3000"
    ingest_interval_minutes: int = 15

    # Demo safety net
    use_seeded_fallback: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton — import `settings` everywhere
settings = Settings()
