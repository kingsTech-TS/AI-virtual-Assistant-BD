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
    CORS_ORIGINS: str = ""
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = r"https://.*\.vercel\.app"

    @property
    def cors_origins(self) -> list[str]:
        raw_origins: list[str] = []
        if self.FRONTEND_URL:
            raw_origins.extend([o.strip().rstrip("/") for o in self.FRONTEND_URL.split(",") if o.strip()])
        if self.CORS_ORIGINS:
            raw_origins.extend([o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()])

        # Always include the known production frontend URL
        raw_origins.append("https://ai-virtual-assistant-kappa.vercel.app")

        # Local development origins
        raw_origins.extend([
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ])

        # Return deduplicated list
        return list(dict.fromkeys(raw_origins))

    LOG_LEVEL: str = "INFO"

    TICKET_START_NUMBER: int = 10000


settings = Settings()
