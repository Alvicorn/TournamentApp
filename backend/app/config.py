# from functools import lru_cache

# from pydantic import Field
# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

#     environment: str = "development"

#     supabase_url: str = ""
#     supabase_key: str = ""

#     redis_url: str = "redis://localhost:6379/0"

#     supabase_jwks_url: str = ""
#     supabase_audience: str = "authenticated"

#     judge_jwt_secret: str = "change-me-in-prod"
#     judge_jwt_ttl_seconds: int = 24 * 60 * 60

#     admin_email_allowlist: str = ""

#     vapid_public_key: str = ""
#     vapid_private_key: str = ""

#     backup_s3_bucket: str = ""
#     aws_region: str = "us-west-2"

#     cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

#     @property
#     def admin_emails(self) -> set[str]:
#         return {e.strip().lower() for e in self.admin_email_allowlist.split(",") if e.strip()}


# @lru_cache
# def get_settings() -> Settings:
#     return Settings()
