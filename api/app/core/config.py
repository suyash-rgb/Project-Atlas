from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Atlas - Report Copilot API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    CORS_ALLOWED_ORIGINS: list[str] = [
        "*",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    DB_TYPE: str = "sqlite"
    SQLITE_DB_PATH: str = str(REPOSITORY_ROOT / "data" / "atlas.db")

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "project_atlas"
    MYSQL_USER: Optional[str] = None
    MYSQL_PASSWORD: Optional[str] = None
    MYSQL_READONLY_USER: Optional[str] = None
    MYSQL_READONLY_PASSWORD: Optional[str] = None

    # Vector Database (ChromaDB)
    CHROMA_PERSIST_DIRECTORY: str = str(REPOSITORY_ROOT / "data" / "chroma_db")
    REPORTS_DIR: str = str(REPOSITORY_ROOT / "data" / "reports")
    CHART_CACHE_DIR: str = str(REPOSITORY_ROOT / "data" / "chart_summaries")

    # Langfuse Observability
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: Optional[str] = None

    # Redis Semantic Cache
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.90
    SEMANTIC_CACHE_TTL_SECONDS: int = 86400

    model_config = SettingsConfigDict(
        env_file=str(REPOSITORY_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
