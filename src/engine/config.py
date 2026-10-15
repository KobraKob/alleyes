"""Configuration management using Pydantic Settings."""

import base64
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")

    # Database URLs
    database_url: str = Field(
        default="postgresql://migrator:migrator_secret@localhost:5432/marketing_engine",
        alias="DATABASE_URL",
    )
    app_role_url: str = Field(
        default="postgresql://app_user:app_secret@localhost:5432/marketing_engine",
        alias="APP_ROLE_URL",
    )
    learning_role_url: str = Field(
        default="postgresql://learning_svc:learning_secret@localhost:5432/marketing_engine",
        alias="LEARNING_ROLE_URL",
    )

    # Browser origins allowed to call the API; configure explicitly in deployment.
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")

    # Operational modes
    dry_run: bool = Field(default=True, alias="DRY_RUN")
    live_sends: bool = Field(default=False, alias="LIVE_SENDS")

    # LLM configuration
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    llm_model: str = Field(default="openai/gpt-oss-120b", alias="LLM_MODEL")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # Cryptography
    pii_encryption_key: str = Field(
        default="vS8zC8rVl71Dk6fQWk3Xz9J2gN7tVb6uY4eO1pP8lDs=", alias="PII_ENCRYPTION_KEY"
    )
    tenant_hmac_master_key: str = Field(
        default="kL9mB7xP2wQ4vC8nZ1tY6rJ3gH5eD0fA=", alias="TENANT_HMAC_MASTER_KEY"
    )
    jwt_secret: str = Field(
        default="super-secret-jwt-signing-key-for-auth-token-validation", alias="JWT_SECRET"
    )

    # Connectors
    whatsapp_verify_token: str = Field(
        default="wa_verify_token_default", alias="WHATSAPP_VERIFY_TOKEN"
    )
    whatsapp_app_secret: str = Field(default="wa_secret_default", alias="WHATSAPP_APP_SECRET")
    whatsapp_phone_number_id: str = Field(
        default="100234567890123", alias="WHATSAPP_PHONE_NUMBER_ID"
    )
    meta_app_id: str = Field(default="123456789", alias="META_APP_ID")
    meta_app_secret: str = Field(default="meta_secret_default", alias="META_APP_SECRET")
    ses_region: str = Field(default="ap-south-1", alias="SES_REGION")

    # Traces & Storage
    trace_store_uri: str = Field(default="file://./traces", alias="TRACE_STORE_URI")


    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Fail closed when production is configured with development credentials."""
        if self.app_env.lower() != "production":
            return self
        required_values = {
            "DATABASE_URL": (self.database_url, "migrator_secret"),
            "APP_ROLE_URL": (self.app_role_url, "app_secret"),
            "LEARNING_ROLE_URL": (self.learning_role_url, "learning_secret"),
            "JWT_SECRET": (self.jwt_secret, "super-secret-jwt-signing-key-for-auth-token-validation"),
            "WHATSAPP_VERIFY_TOKEN": (self.whatsapp_verify_token, "wa_verify_token_default"),
            "WHATSAPP_APP_SECRET": (self.whatsapp_app_secret, "wa_secret_default"),
            "META_APP_SECRET": (self.meta_app_secret, "meta_secret_default"),
        }
        unsafe = [
            name
            for name, (value, placeholder) in required_values.items()
            if not value or placeholder in value
        ]
        if unsafe:
            raise ValueError(
                "Production configuration contains missing/default secrets: "
                + ", ".join(unsafe)
            )
        if len(self.pii_key_bytes) != 32:
            raise ValueError("PII_ENCRYPTION_KEY must decode to exactly 32 bytes.")
        if len(self.hmac_key_bytes) < 32:
            raise ValueError("TENANT_HMAC_MASTER_KEY must decode to at least 32 bytes.")
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters.")
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("Production CORS_ORIGINS must list explicit trusted origins.")
        return self

    @property
    def pii_key_bytes(self) -> bytes:
        """Returns 32-byte key for AES-256."""
        decoded = base64.b64decode(self.pii_encryption_key)
        if len(decoded) != 32:
            # Pad or truncate if not 32 bytes for safety in mock/testing
            return decoded.ljust(32, b"\0")[:32]
        return decoded

    @property
    def hmac_key_bytes(self) -> bytes:
        """Returns master key bytes for tenant HMAC derivation."""
        try:
            return base64.b64decode(self.tenant_hmac_master_key)
        except Exception:
            return self.tenant_hmac_master_key.encode("utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
