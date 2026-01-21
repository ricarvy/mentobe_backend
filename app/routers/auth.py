from fastapi import APIRouter, Depends, HTTPException, status
from app.models import (
    LoginRequest, RegisterRequest, UserResponse, 
    SuccessResponse, ErrorResponse, QuotaResponse
)
from app.dependencies import get_current_user, verify_password, get_password_hash
from app.database import supabase
from app.config import settings
from app.services.quota import QuotaService
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=SuccessResponse)
async def login(request: LoginRequest):
    """
    用户登录接口
    支持演示账号和普通账号
    """
    logger.info(f"Login attempt for email: {request.email}")
    
    # Check demo account
    if settings.DEMO_ACCOUNT_ENABLED and request.email == settings.DEMO_ACCOUNT_EMAIL:
        if request.password == settings.DEMO_ACCOUNT_PASSWORD:
            logger.info("Demo account login successful")
            
            # Sync demo user to DB to ensure foreign key constraints work for payments
            try:
                # Check if demo user exists (using a fixed UUID for demo user to be consistent)
                demo_uuid = "00000000-0000-0000-0000-000000000000" 
                resp = supabase.table("users").select("*").eq("id", demo_uuid).execute()
                
                if not resp.data:
                    # Create demo user if not exists
                    demo_user = {
                        "id": demo_uuid,
                        "email": request.email,
                        "password": get_password_hash(request.password),
                        "username": "Demo User",
                        "is_active": True,
                        "created_at": datetime.now().isoformat(),
                        "quota": 999999,
                        "vip_level": 0
                    }
                    supabase.table("users").insert(demo_user).execute()
                    logger.info("Demo user created in DB")
                else:
                    # Ensure it's active and has correct email
                    # Also fetch latest VIP status
                    pass
                
                # Fetch latest data to return correct VIP status
                resp = supabase.table("users").select("*").eq("id", demo_uuid).execute()
                user_data = resp.data[0]
                
                return SuccessResponse(data=UserResponse(
                    id=user_data["id"],
                    username=user_data["username"],
                    email=user_data["email"],
                    isActive=user_data.get("is_active", True),
                    isDemo=True,
                    unlimitedQuota=True,
                    vipLevel=user_data.get("vip_level", 0),
                    vipExpireAt=user_data.get("vip_expire_at")
                ))
            except Exception as e:
                logger.error(f"Failed to sync demo user to DB: {e}")
                # Fallback to in-memory response if DB fails, though payments might fail
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
             logger.warning(f"Login failed: User not found for {request.email}")
             raise HTTPException(status_code=401, detail="邮箱或密码错误")
        
        user_data = response.data[0]
        if not verify_password(request.password, user_data["password"]):
            logger.warning(f"Login failed: Invalid password for {request.email}")
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
            
        logger.info(f"User {user_data['id']} logged in successfully")
        return SuccessResponse(data=UserResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            isActive=user_data.get("is_active", True),
            isDemo=False,
            unlimitedQuota=False,
            vipLevel=user_data.get("vip_level", 0),
            vipExpireAt=user_data.get("vip_expire_at")
        ))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})

@router.post("/register", response_model=SuccessResponse)
async def register(request: RegisterRequest):
    """
    用户注册接口
    """
    logger.info(f"Register attempt for email: {request.email}")
    try:
        # Check if user exists
        response = supabase.table("users").select("id").eq("email", request.email).execute()
        if response.data:
            logger.warning(f"Register failed: Email {request.email} already exists")
            return ErrorResponse(success=False, error={"code": "USER_EXISTS", "message": "该邮箱已被注册"})
            
        hashed_pw = get_password_hash(request.password)
        username = request.email.split("@")[0]
        
        new_user = {
            "email": request.email,
            "password": hashed_pw,
            "username": username,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "quota": 3 # Initialize with default quota
        }
        
        insert_response = supabase.table("users").insert(new_user).execute()
        if not insert_response.data:
             logger.error("Failed to insert user into DB")
             raise Exception("创建用户失败")
             
        created_user = insert_response.data[0]
        logger.info(f"User {created_user['id']} registered successfully")
        
        return SuccessResponse(data=UserResponse(
            id=created_user["id"],
            username=created_user["username"],
            email=created_user["email"],
            isActive=created_user["is_active"]
        ))
        
    except Exception as e:
        logger.error(f"Register error: {e}")
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})

@router.get("/quota", response_model=SuccessResponse)
async def get_quota(userId: str, current_user: UserResponse = Depends(get_current_user)):
    # Ensure checking own quota
    if userId != current_user.id:
        pass 
        
    try:
        quota_info = await QuotaService.get_user_quota(current_user.id, current_user.isDemo)
        return SuccessResponse(data=quota_info)
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})
