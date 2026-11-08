from typing import Any, List, Union, Optional
from urllib.parse import urlparse
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    # Project Information
    APP_NAME: str = "VyapaarSetu"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Security
    SECRET_KEY: str = Field(default="temporary-dev-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # Database Configuration (PostgreSQL)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "12345"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "vyapaarsetu_db"
    
    # Complete Database Async URL
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:12345@127.0.0.1:5432/vyapaarsetu_db"
    )

    # CORS Origins (accepts comma-separated string or list)
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    )

    # AI Provider ("gemini", "openai", or "auto")
    AI_PROVIDER: str = "auto"

    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TIMEOUT_SECONDS: int = 15

    # Gemini Configuration
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_TIMEOUT_SECONDS: int = 20

    # Scheme Engine Stacking Policy
    # Options: "FLAG_CONFLICT_FOR_REVIEW" (default, safe), "BEST_VALUE", "ALLOW_STACKING"
    ALLOW_SCHEME_STACKING: bool = False
    SCHEME_STACKING_POLICY: str = "FLAG_CONFLICT_FOR_REVIEW"

    # Credit & Inventory Policies
    STRICT_CREDIT_HOLD: bool = True
    INSUFFICIENT_STOCK_POLICY: str = "REJECT_ORDER"  # Never silently create partial orders

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Any) -> str:
        if isinstance(v, str):
            url = v.strip()
            # Convert standard PostgreSQL scheme prefixes to SQLAlchemy asyncpg dialect
            if url.startswith("postgres://"):
                url = "postgresql+asyncpg://" + url[len("postgres://"):]
            elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
                url = "postgresql+asyncpg://" + url[len("postgresql://"):]
            # Normalize sslmode to ssl for asyncpg
            if "sslmode=require" in url:
                url = url.replace("sslmode=require", "ssl=require")
            return url
        return str(v)

    @model_validator(mode="after")
    def sync_database_host_and_port(self) -> "Settings":
        try:
            parsed = urlparse(self.DATABASE_URL)
            if parsed.hostname:
                self.POSTGRES_HOST = parsed.hostname
            if parsed.port:
                self.POSTGRES_PORT = parsed.port
            elif parsed.hostname and self.POSTGRES_PORT == 5432:
                self.POSTGRES_PORT = 5432
        except Exception:
            pass
        return self

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "t", "debug", "dev", "development")
        return False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
