from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_audience: str = "authenticated"

    database_url: str = ""  # e.g. postgresql+psycopg://user:pass@host/db

    redis_url: str = ""

    judge_jwt_secret: str = ""
    judge_jwt_ttl_seconds: int = 24 * 60 * 60

    admin_email_allowlist: str = ""

    vapid_public_key: str = ""
    vapid_private_key: str = ""

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8080"])

    # S3 backup storage
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_email_allowlist.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
