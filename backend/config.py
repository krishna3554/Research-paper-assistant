from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore" 
    )

    llm_provider: str = Field(default="llmstudio", alias="LLM_PROVIDER")

    lm_studio_url: str | None = Field(default=None, alias="LLM_STUDIO_URL")
    lm_studio_api_key: str | None = Field(default=None, alias="LLM_STUDIO_API_KEY")
    lm_studio_model_name: str | None = Field(default=None, alias="LLM_STUDIO_MODEL_NAME")

    openrouter_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_URL",
    )
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="deepseek/deepseek-chat-v3-0324",
        alias="OPENROUTER_MODEL",
    )

    database_url: str = Field(alias="DATABASE_URL")

    storage_provider: str = Field(default="minio", alias="STORAGE_PROVIDER")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME")
    s3_access_key_id: str = Field(alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(alias="S3_SECRET_ACCESS_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    chroma_dir: str = Field(default="chroma_db", alias="CHROMA_DIR")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()