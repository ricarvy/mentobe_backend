from fastapi import APIRouter, Depends, HTTPException, status
from app.models import (
    LoginRequest, RegisterRequest, UserResponse, 
    SuccessResponse, ErrorResponse, QuotaResponse
)
from app.dependencies import get_current_user, verify_password, get_password_hash
from app.database import supabase
from app.config import settings
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=SuccessResponse)
async def login(request: LoginRequest):
    # Check demo account
    if settings.DEMO_ACCOUNT_ENABLED and request.email == settings.DEMO_ACCOUNT_EMAIL:
        if request.password == settings.DEMO_ACCOUNT_PASSWORD:
            return SuccessResponse(data=UserResponse(
                id="demo-user-id",
                username="Demo User",
                email=request.email,
                isActive=True,
                isDemo=True,
                unlimitedQuota=True
            ))
    
    # Check DB
    try:
        response = supabase.table("users").select("*").eq("email", request.email).execute()
        if not response.data:
             raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user_data = response.data[0]
        if not verify_password(request.password, user_data["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        return SuccessResponse(data=UserResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            isActive=user_data.get("is_active", True),
            isDemo=False,
            unlimitedQuota=False
        ))
    except HTTPException:
        raise
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})

@router.post("/register", response_model=SuccessResponse)
async def register(request: RegisterRequest):
    try:
        # Check if user exists
        response = supabase.table("users").select("id").eq("email", request.email).execute()
        if response.data:
            return ErrorResponse(success=False, error={"code": "USER_EXISTS", "message": "Email already exists"})
            
        hashed_pw = get_password_hash(request.password)
        username = request.email.split("@")[0]
        
        new_user = {
            "email": request.email,
            "password": hashed_pw,
            "username": username,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        
        insert_response = supabase.table("users").insert(new_user).execute()
        if not insert_response.data:
             raise Exception("Failed to create user")
             
        created_user = insert_response.data[0]
        return SuccessResponse(data=UserResponse(
            id=created_user["id"],
            username=created_user["username"],
            email=created_user["email"],
            isActive=created_user["is_active"]
        ))
        
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})

@router.get("/quota", response_model=SuccessResponse)
async def get_quota(userId: str, current_user: UserResponse = Depends(get_current_user)):
    # Demo user
    if current_user.isDemo:
        return SuccessResponse(data=QuotaResponse(
            remaining=999999,
            used=0,
            total="Unlimited",
            isDemo=True
        ))
        
    # Regular user
    # Ensure checking own quota
    if userId != current_user.id:
        # For simplicity, just return current user's quota or error.
        # Strict adherence: return 403 or just process for current_user
        pass 
        
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check quota table
        # We assume a 'daily_quotas' table: user_id, date, count
        response = supabase.table("daily_quotas").select("*").eq("user_id", current_user.id).eq("date", today).execute()
        
        used = 0
        if response.data:
            used = response.data[0]["count"]
            
        # Default free quota = 3 (from spec)
        total = 3
        remaining = max(0, total - used)
        
        return SuccessResponse(data=QuotaResponse(
            remaining=remaining,
            used=used,
            total=total,
            isDemo=False
        ))
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})
