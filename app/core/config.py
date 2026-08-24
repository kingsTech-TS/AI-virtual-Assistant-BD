from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Academic Support Chatbot"
    APP_ENV: str = "development"
    DEBUG: bool = False

    MONGODB_URI: str
    MONGODB_DATABASE: str = "academic_chatbot"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None

    # Rate-limit controls: keep gateway calls per message to a minimum.
    # When False, intent uses keyword matching and RAG uses keyword search,
    # so only response generation hits the gateway (1 call/message instead of 3).
    # Set True once the account has headroom (e.g. after adding credits).
    USE_LLM_INTENT: bool = False
    USE_QUERY_EMBEDDINGS: bool = False

    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: Optional[str] = None
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_DIMENSIONS: int = 1536

    VECTOR_SEARCH_INDEX: str = "vector_index"
    RAG_MIN_RELEVANCE_SCORE: float = 0.60
    RAG_TOP_CANDIDATES: int = 8
    RAG_FINAL_CHUNKS: int = 4

    FRONTEND_URL: str = "http://localhost:3000"

    LOG_LEVEL: str = "INFO"

    TICKET_START_NUMBER: int = 10000


settings = Settings()
