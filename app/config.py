from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Universal RAG PoC"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/rag"
    redis_url: str = "redis://redis:6379/0"
    rq_queue_name: str = "ingestion"

    s3_endpoint: str = "http://minio:9000"
    s3_public_endpoint: str | None = None
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rag-documents"
    s3_region: str = "us-east-1"
    s3_presign_expire_sec: int = 3600

    embedding_provider: Literal["gemini"] = "gemini"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 1536

    llm_provider: Literal["gemini"] = "gemini"
    llm_model: str = "gemini-2.0-flash"
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    vector_top_k: int = 10
    keyword_top_k: int = 10
    answer_context_chunks: int = 5
    answer_context_text_max_chars: int = 1000
    llm_retry_attempts: int = 2
    retrieval_score_threshold: float = 0.25

    chunk_size_chars: int = 4200
    chunk_overlap_chars: int = 500
    pdf_min_text_chars_per_page: int = 40
    image_only_pdf_ratio_threshold: float = 0.5
    pdf_ocr_enabled: bool = True
    pdf_ocr_model: str = "gemini-2.0-flash"
    pdf_ocr_max_pages_per_doc: int = 5

    @property
    def cors_origins_list(self) -> List[str]:
        value = self.cors_origins
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return ["http://localhost:3000"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
