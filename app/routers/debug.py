from fastapi import APIRouter
from app.config import settings
from app.models import SuccessResponse
from datetime import datetime

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/config", response_model=SuccessResponse)
async def get_config():
    return SuccessResponse(data={
        "timestamp": datetime.now().isoformat(),
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION
        },
        "demoAccount": {
            "enabled": settings.DEMO_ACCOUNT_ENABLED,
            "email": settings.DEMO_ACCOUNT_EMAIL
        }
    })

@router.get("/demo-account", response_model=SuccessResponse)
async def get_demo_account():
    return SuccessResponse(data={
        "enabled": settings.DEMO_ACCOUNT_ENABLED,
        "email": settings.DEMO_ACCOUNT_EMAIL,
        "password": "Masked"
    })
