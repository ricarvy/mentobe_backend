from fastapi import APIRouter
from app.config import settings
from app.models import SuccessResponse
from datetime import datetime

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/config", response_model=SuccessResponse)
async def get_config():
    return SuccessResponse(data={
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "NODE_ENV": "development", # In a real app, get from env
            "APP_NAME": settings.APP_NAME,
            "APP_URL": "http://localhost:8000", # Adjusted port
            "APP_VERSION": settings.APP_VERSION
        },
        "llm": {
            "config": {
                "model": settings.LLM_MODEL,
                "temperature": settings.LLM_TEMPERATURE,
                "thinking": "enabled",
                "systemPromptLength": len(settings.TAROT_SYSTEM_PROMPT)
            },
            "isValid": True
        },
        "database": {
            "config": {},
            "isValid": True
        },
        "app": {
            "config": {
                "app": {
                    "name": settings.APP_NAME,
                    "description": "AI-Powered Tarot Readings"
                },
                "features": {
                    "dailyQuota": {
                        "free": 3,
                        "paid": 999
                    },
                    "aiInterpretation": {
                        "enabled": True
                    }
                }
            },
            "isValid": True
        },
        "demoAccount": {
            "enabled": settings.DEMO_ACCOUNT_ENABLED,
            "email": settings.DEMO_ACCOUNT_EMAIL,
            "passwordLength": len(settings.DEMO_ACCOUNT_PASSWORD),
            "id": "demo-user-id"
        }
    })

@router.get("/demo-account", response_model=SuccessResponse)
async def get_demo_account():
    pw = settings.DEMO_ACCOUNT_PASSWORD
    masked = "*" * len(pw)
    chars = []
    if len(pw) >= 2:
        chars.append({"char": pw[0], "code": ord(pw[0])})
        chars.append({"char": pw[1], "code": ord(pw[1])})
        
    return SuccessResponse(data={
        "enabled": settings.DEMO_ACCOUNT_ENABLED,
        "email": settings.DEMO_ACCOUNT_EMAIL,
        "passwordLength": len(pw),
        "passwordMasked": masked,
        "passwordChars": chars,
        "environment": "development",
        "envDemoEmail": settings.DEMO_ACCOUNT_EMAIL,
        "envDemoPassword": "SET" if pw else "UNSET",
        "envDemoEnabled": str(settings.DEMO_ACCOUNT_ENABLED).lower()
    })
