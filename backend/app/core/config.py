from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "SuperAgent RAG"
    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/text-embedding-004"
    composio_api_key: str = ""
    chroma_persist_dir: str = ".chroma"
    chroma_collection: str = "superagent_memory"
    max_upload_bytes: int = 2_000_000
    max_upload_chunks: int = 80
    allowed_upload_extensions: str = ".txt,.md,.markdown,.csv,.json,.log,.py,.js,.ts,.tsx,.html,.css,.pdf,.docx"

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
