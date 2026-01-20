from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str
    
    # App Config
    APP_NAME: str = "Mentob AI"
    APP_VERSION: str = "1.0.0"
    
    # LLM Config
    LLM_MODEL: str = "doubao-seed-1-6-thinking-250715"
    LLM_TEMPERATURE: float = 0.8
    
    # Demo Account
    DEMO_ACCOUNT_ENABLED: bool = True
    DEMO_ACCOUNT_EMAIL: str = "demo@mentobai.com"
    DEMO_ACCOUNT_PASSWORD: str = "Demo123!"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
