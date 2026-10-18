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

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "project_atlas"
    MYSQL_USER: Optional[str] = None
    MYSQL_PASSWORD: Optional[str] = None
    MYSQL_READONLY_USER: Optional[str] = None
    MYSQL_READONLY_PASSWORD: Optional[str] = None

    # Vector Database (ChromaDB)
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"

    # Langfuse Observability
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(REPOSITORY_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
