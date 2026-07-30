"""Application configuration, loaded from environment (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "dev-only-change-me-in-production-please-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    api_env: str = "development"
    api_title: str = "AutoBid Intelligence API"
    api_version: str = "0.1.0"

    # Database. Default to a local SQLite file so the app boots without Postgres for dev/tests;
    # Docker Compose supplies the Postgres async URL.
    database_url: str = "sqlite+aiosqlite:///./autobid.db"
    database_url_sync: str = "sqlite:///./autobid.db"

    # Auth
    jwt_secret_key: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    # Security
    cors_origins: str = "http://localhost:3000"
    cookie_secure: bool = False
    cookie_domain: str = ""
    cookie_samesite: str = "lax"
    auth_rate_limit_per_minute: int = 10
    public_write_rate_limit_per_minute: int = 6      # enquiries / briefs / vet requests
    mot_check_rate_limit_per_minute: int = 12        # public DVSA MOT lookups

    # Media (uploaded storefront photos). Served by the API at /media; point media_base_url at the
    # API's public origin so the storefront can load them cross-origin. Use a persistent volume/bucket.
    media_dir: str = "./media"
    media_base_url: str = "http://localhost:8000"

    # Domain defaults
    vat_rate: float = 0.20
    default_target_profit: float = 1200.0
    default_min_roi: float = 0.15
    default_mandatory_reserve: float = 150.0

    # AI advisor (Claude vision). If no API key is set, a labelled mock adapter is used instead.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # Official UK government vehicle-data APIs (free). Used for registration look-up when configured.
    dvla_ves_api_key: str = ""
    dvla_ves_url: str = (
        "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles")
    dvsa_mot_api_key: str = ""
    dvsa_mot_client_id: str = ""
    dvsa_mot_client_secret: str = ""
    dvsa_mot_token_url: str = ""
    dvsa_mot_scope: str = "https://tapi.dvsa.gov.uk/.default"
    dvsa_mot_url: str = "https://history.mot.api.gov.uk/v1/trade/vehicles/registration"

    # eBay Browse API (parts sourcing). Free developer keys; mock fallback when unset.
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_env: str = "production"  # or "sandbox"
    ebay_marketplace: str = "EBAY_GB"

    @property
    def claude_vision_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def ebay_enabled(self) -> bool:
        return bool(self.ebay_client_id and self.ebay_client_secret)

    @property
    def dvla_ves_enabled(self) -> bool:
        return bool(self.dvla_ves_api_key)

    @property
    def dvsa_mot_enabled(self) -> bool:
        return bool(self.dvsa_mot_api_key and self.dvsa_mot_client_id
                    and self.dvsa_mot_client_secret and self.dvsa_mot_token_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.api_env.lower() in ("production", "prod")

    @property
    def secure_cookies(self) -> bool:
        """Always secure in production, regardless of the cookie_secure toggle."""
        return self.cookie_secure or self.is_production

    @model_validator(mode="after")
    def _normalise_database_url(self) -> Settings:
        """Accept a plain postgres URL (e.g. Railway/Supabase DATABASE_URL) and add the drivers.

        Railway/Supabase provide `postgres://` or `postgresql://`; SQLAlchemy async needs
        `postgresql+asyncpg://` and Alembic (sync) needs `postgresql+psycopg://`.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            self.database_url = "postgresql+asyncpg://" + url[len("postgresql://"):]
            self.database_url_sync = "postgresql+psycopg://" + url[len("postgresql://"):]
        return self

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> Settings:
        if self.is_production:
            secret = self.jwt_secret_key or ""
            if secret == _DEFAULT_JWT_SECRET or len(secret) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong value (>= 32 chars) when API_ENV is "
                    "production. Refusing to start with the default/weak secret."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
