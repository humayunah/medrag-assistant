from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in repo root (one level up from backend/)
_env_file = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "development"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Database
    DATABASE_URL: str = ""
    DATABASE_POOL_URL: str = ""

    # LLM Providers
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    HF_API_TOKEN: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_QUERY: int = 10  # per minute
    RATE_LIMIT_UPLOAD: int = 20  # per hour
    RATE_LIMIT_DEMO: int = 30  # per hour per IP

    # File Upload
    MAX_FILE_SIZE_MB: int = 10

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
