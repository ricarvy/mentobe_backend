from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from app.models import (
    LoginRequest, RegisterRequest, UserResponse, 
    SuccessResponse, ErrorResponse, QuotaResponse,
    SocialLoginRequest
)
from app.dependencies import get_current_user, verify_password, get_password_hash
from app.database import get_db, SessionLocal
from sqlalchemy.orm import Session
from app.db_models import User
from app.config import settings
from app.services.quota import QuotaService
from app.services.auth_social import SocialAuthService
from app.utils.security import create_access_token
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
        
        # Create Access Token
        access_token = create_access_token(data={"sub": user.email})
        
        return SuccessResponse(data=UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            isActive=user.is_active,
            isDemo=False,
            unlimitedQuota=True if user.vip_level and user.vip_level > 0 else False,
            vipLevel=user.vip_level,
            vipExpireAt=user.vip_expire_at.isoformat() if user.vip_expire_at else None,
            accessToken=access_token
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

# --- OAuth Login Rewrite ---

@router.get("/login/{provider}")
async def login_via_provider(provider: str, request: Request, next: str = "/"):
    """
    Initiate OAuth login for provider (google, apple)
    """
    try:
        request.session['next'] = next
        client = SocialAuthService.get_oauth_client(provider)
        # Build redirect URI: e.g. https://domain.com/api/auth/callback/google
        # Ensure _external=True (or absolute URI) is used if behind proxy, handled by starlette_client usually if configured correctly
        redirect_uri = request.url_for('auth_callback', provider=provider)
        
        logger.info(f"Initiating {provider} login.")
        logger.info(f"Generated Redirect URI: {redirect_uri}")
        logger.info(f"Client ID used: {client.client_id}")
        
        # Add prompt='select_account' for Google to force account selection
        kwargs = {}
        if provider == 'google':
            kwargs['prompt'] = 'select_account'
            
        return await client.authorize_redirect(request, redirect_uri, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth init error: {e}")
        raise HTTPException(status_code=500, detail="Authentication initiation failed")

@router.get("/callback/{provider}")
async def auth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """
    Handle OAuth callback
    """
    try:
        client = SocialAuthService.get_oauth_client(provider)
        token = await client.authorize_access_token(request)
        
        user_info = token.get('userinfo')
        if not user_info and 'id_token' in token:
            user_info = await client.parse_id_token(request, token)

        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        email = user_info.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in user info")

        # Check/Create User
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                username=user_info.get('name') or email.split("@")[0],
                is_active=True,
                created_at=datetime.now(),
                quota=3,
                password=None
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create Access Token
        access_token = create_access_token(data={"sub": user.email})
        
        # Prepare User Data (Same structure as login response)
        user_response = UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            isActive=user.is_active,
            isDemo=False,
            unlimitedQuota=True if user.vip_level and user.vip_level > 0 else False,
            vipLevel=user.vip_level,
            vipExpireAt=user.vip_expire_at.isoformat() if user.vip_expire_at else None,
            accessToken=access_token
        )
        
        # Redirect to frontend with token and user data
        import json
        import urllib.parse
        
        next_path = request.session.pop('next', '/')
        
        # Force /google_login_successed if provider is google and next is default
        if provider == 'google' and next_path == '/':
            next_path = '/google_login_successed'
            
        # If next_path is relative, prepend FRONTEND_URL
        if not next_path.startswith(('http://', 'https://')):
            # Ensure FRONTEND_URL doesn't end with slash if next_path starts with slash
            base_url = settings.FRONTEND_URL.rstrip('/')
            path = next_path.lstrip('/')
            redirect_url = f"{base_url}/{path}"
        else:
            redirect_url = next_path
            
        # Serialize user data
        user_data_json = json.dumps(user_response.model_dump())
        encoded_user_data = urllib.parse.quote(user_data_json)
        
        return RedirectResponse(url=f"{redirect_url}?token={access_token}&user={encoded_user_data}")

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        # Redirect to frontend with error
        next_path = request.session.pop('next', '/')
        
        if not next_path.startswith(('http://', 'https://')):
            base_url = settings.FRONTEND_URL.rstrip('/')
            path = next_path.lstrip('/')
            redirect_url = f"{base_url}/{path}"
        else:
            redirect_url = next_path
            
        return RedirectResponse(url=f"{redirect_url}?error=auth_failed&message={str(e)}")
