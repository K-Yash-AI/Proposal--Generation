"""
Central configuration using pydantic-settings.
All settings are loaded from environment variables / .env file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Anthropic ────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(..., validation_alias="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-opus-4-6", validation_alias="CLAUDE_MODEL")

    # ── Fireflies ────────────────────────────────────────────────────────────
    fireflies_api_key: str = Field(..., validation_alias="FIREFLIES_API_KEY")
    fireflies_api_url: str = "https://api.fireflies.ai/graphql"
    fireflies_transcripts_limit: int = Field(5, validation_alias="FIREFLIES_TRANSCRIPTS_LIMIT")

    # ── Google Docs ──────────────────────────────────────────────────────────
    google_service_account_file: Optional[str] = Field(
        None, validation_alias="GOOGLE_SERVICE_ACCOUNT_FILE"
    )
    google_credentials_file: Optional[str] = Field(
        None, validation_alias="GOOGLE_CREDENTIALS_FILE"
    )
    google_token_file: str = Field("token.json", validation_alias="GOOGLE_TOKEN_FILE")
    google_template_doc_id: Optional[str] = Field(
        None, validation_alias="GOOGLE_TEMPLATE_DOC_ID"
    )

    # ── Company Info ─────────────────────────────────────────────────────────
    company_name: str = Field("Frutitions", validation_alias="COMPANY_NAME")
    company_tagline: str = Field(
        "Turning Ideas Into Reality", validation_alias="COMPANY_TAGLINE"
    )
    company_website: str = Field(
        "https://frutitions.com", validation_alias="COMPANY_WEBSITE"
    )
    company_email: str = Field(
        "hello@frutitions.com", validation_alias="COMPANY_EMAIL"
    )
    company_phone: str = Field(
        "+1 (555) 000-0000", validation_alias="COMPANY_PHONE"
    )

    # ── Output ───────────────────────────────────────────────────────────────
    output_dir: str = Field("./proposals", validation_alias="OUTPUT_DIR")

    @field_validator("output_dir")
    @classmethod
    def ensure_output_dir(cls, v: str) -> str:
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


# Singleton instance
settings = Settings()
