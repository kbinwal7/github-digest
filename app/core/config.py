from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    github_token: str | None = None
    gemini_api_key: str | None = None
    gemini_generation_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "github-issue-digest"
    github_page_size: int = 100
    github_max_pages: int = 10
    stale_after_days: int = 730
    issue_text_max_chars: int = 8000
    app_name: str = "GitHub Digest"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
