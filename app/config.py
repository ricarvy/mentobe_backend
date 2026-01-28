from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # App Config
    APP_NAME: str
    APP_VERSION: str
    
    # LLM Config
    LLM_MODEL: str
    LLM_TEMPERATURE: float
    ARK_API_KEY: str
    ARK_BASE_URL: str
    TAROT_SYSTEM_PROMPT: str
    TAROT_FOLLOWUP_COUNT: int = 3
    
    # Demo Account
    DEMO_ACCOUNT_ENABLED: bool
    DEMO_ACCOUNT_EMAIL: str
    DEMO_ACCOUNT_PASSWORD: str

    # Stripe Config
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_API_BASE: str

    # Stripe Prices
    NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY: str
    NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY: str
    NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY: str
    NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY: str
    
    # Auth Config
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    APPLE_CLIENT_ID: str
    APPLE_CLIENT_SECRET: str
    
    # Frontend Config
    FRONTEND_URL: str = "http://localhost:8899"
    API_BASE_URL: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
