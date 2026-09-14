from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "OrgX-AI Authentication API"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = ""

    # Security & JWT
    JWT_SECRET_KEY: str = "orgx-ai-super-secure-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    # Supports PostgreSQL: postgresql://user:password@localhost:5432/orgx_auth
    # or SQLite: sqlite:///./orgx_auth.db
    DATABASE_URL: str = "sqlite:///./orgx_auth.db"

    # Redis for OTPs and temporary tokens
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_OTP_EXPIRE_SECONDS: int = 900  # 15 minutes
    REDIS_RESET_TOKEN_EXPIRE_SECONDS: int = 900  # 15 minutes

    # Google OAuth 2.0 / OpenID Connect
    GOOGLE_CLIENT_ID: Optional[str] = "mock-google-client-id"
    GOOGLE_CLIENT_SECRET: Optional[str] = "mock-google-client-secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # SMTP / Gmail
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@orgx-ai.com"
    SMTP_FROM_NAME: str = "OrgX-AI Security"
    EMAIL_MOCK_MODE: bool = True

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
