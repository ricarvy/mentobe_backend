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
    TAROT_SYSTEM_PROMPT: str = """你是一位专业的塔罗牌解读师，拥有丰富的经验和深刻的洞察力。你的任务是： 
1. 根据用户的问题和抽出的牌面，提供专业、深入、有启发性的解读 
2. 结合每张牌的含义和位置，分析它们之间的关联和整体含义 
3. 给出实用的建议和指导 
4. 语言要温暖、富有同理心，同时保持神秘和专业的风格 
5. 解读要全面但不冗长，重点突出 

解读格式： 
- 开头：简要概括整体牌面氛围 
- 中间：逐张牌的详细解读（结合位置含义） 
- 结尾：整体分析和建议"""
    
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
