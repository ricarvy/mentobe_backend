from fastapi import APIRouter, Depends, HTTPException, status
from app.models import (
    LoginRequest, RegisterRequest, UserResponse, 
    SuccessResponse, ErrorResponse, QuotaResponse
)
from app.dependencies import get_current_user, verify_password, get_password_hash
from app.database import get_db, SessionLocal
from sqlalchemy.orm import Session
from app.db_models import User
from app.config import settings
from app.services.quota import QuotaService
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=SuccessResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
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
                demo_user = db.query(User).filter(User.id == demo_uuid).first()
                
                if not demo_user:
                    # Create demo user if not exists
                    demo_user = User(
                        id=demo_uuid,
                        email=request.email,
                        password=get_password_hash(request.password),
                        username="Demo User",
                        is_active=True,
                        created_at=datetime.now(),
                        quota=999999,
                        vip_level=0
                    )
                    db.add(demo_user)
                    db.commit()
                    db.refresh(demo_user)
                    logger.info("Demo user created in DB")
                
                # Fetch latest data to return correct VIP status
                # demo_user is already refreshed or fetched
                
                return SuccessResponse(data=UserResponse(
                    id=str(demo_user.id),
                    username=demo_user.username,
                    email=demo_user.email,
                    isActive=demo_user.is_active,
                    isDemo=True,
                    unlimitedQuota=True,
                    vipLevel=demo_user.vip_level,
                    vipExpireAt=demo_user.vip_expire_at.isoformat() if demo_user.vip_expire_at else None
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
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
             logger.warning(f"Login failed: User not found for {request.email}")
             raise HTTPException(status_code=401, detail="邮箱或密码错误")
        
        if not verify_password(request.password, user.password):
            logger.warning(f"Login failed: Invalid password for {request.email}")
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
            
        logger.info(f"User {user.id} logged in successfully")
        return SuccessResponse(data=UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            isActive=user.is_active,
            isDemo=False,
            unlimitedQuota=False, # Should we calculate this? Login doesn't return quota usually.
            vipLevel=user.vip_level,
            vipExpireAt=user.vip_expire_at.isoformat() if user.vip_expire_at else None
        ))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="登录失败")

@router.post("/register", response_model=SuccessResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册接口
    """
    logger.info(f"Register attempt for email: {request.email}")
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        if user:
            logger.warning(f"Register failed: Email {request.email} already exists")
            return ErrorResponse(success=False, error={"code": "USER_EXISTS", "message": "该邮箱已被注册"})
            
        hashed_pw = get_password_hash(request.password)
        username = request.email.split("@")[0]
        
        new_user = User(
            email=request.email,
            password=hashed_pw,
            username=username,
            is_active=True,
            created_at=datetime.now(),
            quota=3
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"User {new_user.id} registered successfully")
        
        return SuccessResponse(data=UserResponse(
            id=str(new_user.id),
            username=new_user.username,
            email=new_user.email,
            isActive=new_user.is_active
        ))
        
    except Exception as e:
        logger.error(f"Register error: {e}")
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})

@router.get("/quota", response_model=SuccessResponse)
def get_quota(userId: str, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    # Ensure checking own quota
    if userId != current_user.id:
        pass 
        
    try:
        quota_info = QuotaService.get_user_quota(current_user.id, db, current_user.isDemo)
        return SuccessResponse(data=quota_info)
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "INTERNAL_ERROR", "message": str(e)})
