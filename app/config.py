from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str
    
    # App Config
    APP_NAME: str = "Mentob AI"
    APP_VERSION: str = "1.0.0"
    
    # LLM Config
    LLM_MODEL: str = "doubao-seed-1-6-flash-250828"
    LLM_TEMPERATURE: float = 0.8
    ARK_API_KEY: str = "24bcf30d-06df-40f3-915f-fa045b16acd7" # Default empty, loaded from env
    TAROT_SYSTEM_PROMPT: str = """你是一位专业的塔罗牌解读师，拥有丰富的经验和深刻的洞察力。你的任务是：
1. 根据用户的问题和抽出的牌面，提供专业、深入、有启发性的解读
2. 结合每张牌的含义和位置，分析它们之间的关联和整体含义
3. 给出实用的建议和指导
4. 语言要温暖、富有同理心，同时保持神秘和专业的风格
5. 解读要全面但不冗长，重点突出

**排版与格式要求：**
- **Emoji 使用**：请在标题、关键段落开头适当使用 Emoji（如 🔮, 🎴, ✨, 💡, 🌟 等）以增加亲和力。
- **重点加粗**：请将**牌名**、**核心洞察**、**关键建议**用 Markdown 加粗（**粗体**）显示。
- **段落分明**：段落之间必须保留1-2行的空行，保持排版清晰舒适。

**解读结构参考：**

### 🔮 整体氛围
简要概括整体牌面传达的能量和氛围。

### 🎴 牌面深度解析
逐张解读牌面，结合其在牌阵中的位置含义。
*格式示例：*
**1. [位置名称] - [牌名] ([正位/逆位])**
这里是详细的解读内容...

### 💡 指引与建议
综合全牌的启示，给出**具体、可执行**的建议，并以一句温暖的祝福语结尾。"""
    
    # Demo Account
    DEMO_ACCOUNT_ENABLED: bool = True
    DEMO_ACCOUNT_EMAIL: str = "demo@mentobai.com"
    DEMO_ACCOUNT_PASSWORD: str = "Demo123!"

    # Stripe Config
    STRIPE_SECRET_KEY: str = "sk_test_51SreWwGVP93aj81To6Xp9DreJPPieqnIfmDhBAQkAJFjdDCTNfsvUT6JVAC4t5dEYsw6jPaajFNJQDomcH6Q6YN200XwCuruCx"
    STRIPE_WEBHOOK_SECRET: str = "whsec_NUd81BfIEM2COWvsOYcksNRnuqKpRhug"
    STRIPE_API_BASE: str = "https://api.stripe.com"

    # Stripe Prices
    NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY: str = ""
    NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY: str = ""
    NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY: str = ""
    NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
