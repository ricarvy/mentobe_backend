from fastapi import APIRouter
from app.database import supabase
from app.models import SuccessResponse, ErrorResponse

router = APIRouter(tags=["system"])

@router.post("/init", response_model=SuccessResponse)
async def init_system():
    # Just check DB connection
    try:
        # Try to select from users
        supabase.table("users").select("id").limit(1).execute()
        return SuccessResponse(message="System initialized (DB connected)")
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "DB_ERROR", "message": str(e)})
