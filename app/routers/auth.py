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
import secrets

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
                        login_type="email",
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
                
                # Create token for demo user
                login_token = "demo-login-token" # Fixed token for demo user to simplify
                # demo_user is in DB, we can update it too if we want, but demo user might be shared?
                # If demo user is shared, we shouldn't enforce single session strictness or we use a unique demo ID per session.
                # But the code uses a fixed UUID. 
                # Let's assume demo user doesn't need strict session check or we update it anyway.
                demo_user.login_token = login_token
                db.commit()
                
                access_token = create_access_token(data={"sub": demo_user.email, "login_token": login_token})

                return SuccessResponse(data=UserResponse(
                    id=str(demo_user.id),
                    username=demo_user.username,
                    email=demo_user.email,
                    isActive=demo_user.is_active,
                    isDemo=True,
                    unlimitedQuota=True,
                    vipLevel=demo_user.vip_level,
                    vipExpireAt=demo_user.vip_expire_at.isoformat() if demo_user.vip_expire_at else None,
                    accessToken=access_token,
                    loginToken=login_token
                ))
            except Exception as e:
                logger.error(f"Failed to sync demo user to DB: {e}")
                # Fallback to in-memory response if DB fails, though payments might fail
                login_token = "demo-login-token-fallback"
                access_token = create_access_token(data={"sub": request.email, "login_token": login_token})
                return SuccessResponse(data=UserResponse(
                    id="demo-user-id",
                    username="Demo User",
                    email=request.email,
                    isActive=True,
                    isDemo=True,
                    unlimitedQuota=True,
                    accessToken=access_token,
                    loginToken=login_token
                ))
    
    # Check DB
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
             logger.warning(f"Login failed: User not found for {request.email}")
             raise HTTPException(status_code=401, detail="邮箱或密码错误")
        
        # Check if user is a social login user (no password)
        if not user.password:
            logger.warning(f"Login failed: Social user {request.email} tried password login")
            # Return 403 Forbidden with specific code for frontend to trigger popup
            raise HTTPException(
                status_code=403, 
                detail="SOCIAL_LOGIN_REQUIRED: Please use social login"
            )

        if not verify_password(request.password, user.password):
            logger.warning(f"Login failed: Invalid password for {request.email}")
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
            
        logger.info(f"User {user.id} logged in successfully")
        
        # Generate new login token
        login_token = secrets.token_urlsafe(32)
        user.login_token = login_token
        db.commit()
        
        # Create Access Token
        access_token = create_access_token(data={"sub": user.email, "login_token": login_token})
        
        return SuccessResponse(data=UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            isActive=user.is_active,
            isDemo=False,
            unlimitedQuota=True if user.vip_level and user.vip_level > 0 else False,
            vipLevel=user.vip_level,
            vipExpireAt=user.vip_expire_at.isoformat() if user.vip_expire_at else None,
            accessToken=access_token,
            loginToken=login_token
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
        
        login_token = secrets.token_urlsafe(32)
        new_user = User(
            email=request.email,
            password=hashed_pw,
            username=username,
            login_type="email",
            login_token=login_token,
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
            isActive=new_user.is_active,
            loginToken=login_token
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

@router.get("/me", response_model=SuccessResponse)
def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """
    获取当前登录用户信息 (用于持久化登录验证)
    """
    return SuccessResponse(data=current_user)

# --- OAuth Login Rewrite ---

@router.get("/login/{provider}")
async def login_via_provider(provider: str, request: Request, next: str = "/"):
    """
    Initiate OAuth login for provider (google)
    """
    try:
        request.session['next'] = next
        
        # Determine redirect URI
        if settings.API_BASE_URL:
            redirect_uri = f"{settings.API_BASE_URL.rstrip('/')}/api/auth/callback/{provider}"
        else:
            redirect_uri = str(request.url_for('auth_callback', provider=provider))
            
        logger.info(f"Initiating {provider} login.")
        logger.info(f"Generated Redirect URI: {redirect_uri}")
        
        if provider == 'google':
            state = secrets.token_urlsafe(16)
            auth_url = SocialAuthService.get_google_auth_url(redirect_uri, state)
            
            response = RedirectResponse(url=auth_url)
            
            # Set state cookie for CSRF protection
            secure = True if (settings.API_BASE_URL and settings.API_BASE_URL.startswith("https://")) else False
            response.set_cookie(
                key=f"oauth_state_{provider}",
                value=state,
                domain=".mentobe.co" if secure else None,
                secure=secure,
                httponly=True,
                 samesite="none" if secure else "lax"
            )
            return response
            
        elif provider == 'apple':
            # TODO: Implement manual Apple flow
            raise HTTPException(status_code=501, detail="Apple login temporarily unavailable")
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
            
    except Exception as e:
        logger.error(f"OAuth init error: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication initiation failed: {str(e)}")

@router.get("/callback/{provider}")
async def auth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    try:
        # Validate CSRF State
        cookie_state = request.cookies.get(f"oauth_state_{provider}")
        query_state = request.query_params.get("state")
        
        if not cookie_state:
             logger.error("State cookie missing")
             raise HTTPException(status_code=400, detail="State cookie missing. Please enable cookies.")
             
        if not query_state or query_state != cookie_state:
            logger.error(f"State mismatch: cookie={cookie_state}, query={query_state}")
            raise HTTPException(status_code=400, detail="CSRF Warning! State mismatch.")
            
        # Process Callback
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code missing")
            
        if settings.API_BASE_URL:
            redirect_uri = f"{settings.API_BASE_URL.rstrip('/')}/api/auth/callback/{provider}"
        else:
            redirect_uri = str(request.url_for('auth_callback', provider=provider))
            
        user_info = {}
        if provider == 'google':
            user_info = await SocialAuthService.exchange_google_code(code, redirect_uri)
        else:
             raise HTTPException(status_code=400, detail="Unsupported provider")
             
        # User Logic (Create/Get)
        email = user_info.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in provider response")
            
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Register new user
            login_token = secrets.token_urlsafe(32)
            username = user_info.get('name') or email.split("@")[0]
            user = User(
                email=email,
                username=username,
                is_active=True,
                created_at=datetime.now(),
                quota=3,
                password=None,
                login_type=provider,
                login_token=login_token
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"New social user registered: {email}")
        else:
            logger.info(f"Existing social user logged in: {email}")
            
            # Generate new login token
            login_token = secrets.token_urlsafe(32)
            user.login_token = login_token
            db.commit()
            
        # Create Token
        access_token = create_access_token(data={"sub": user.email, "login_token": login_token})
        
        # Prepare User Data
        user_response = UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            isActive=user.is_active,
            isDemo=False,
            unlimitedQuota=True if user.vip_level and user.vip_level > 0 else False,
            vipLevel=user.vip_level,
            vipExpireAt=user.vip_expire_at.isoformat() if user.vip_expire_at else None,
            accessToken=access_token,
            loginToken=login_token
        )
        
        # Redirect
        import json
        import urllib.parse
        
        next_path = request.session.pop('next', '/')
        
        if provider == 'google' and next_path == '/':
            next_path = '/google_login_successed'
            
        if not next_path.startswith(('http://', 'https://')):
            base_url = settings.FRONTEND_URL.rstrip('/')
            path = next_path.lstrip('/')
            redirect_url = f"{base_url}/{path}"
        else:
            redirect_url = next_path
            
        user_data_json = json.dumps(user_response.model_dump())
        encoded_user_data = urllib.parse.quote(user_data_json)
        
        final_url = f"{redirect_url}?token={access_token}&user={encoded_user_data}"
        if '?' in redirect_url:
             final_url = f"{redirect_url}&token={access_token}&user={encoded_user_data}"
             
        response = RedirectResponse(url=final_url)
        
        secure = True if (settings.API_BASE_URL and settings.API_BASE_URL.startswith("https://")) else False
        response.delete_cookie(key=f"oauth_state_{provider}", domain=".mentobe.co" if secure else None)
        
        return response

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        next_path = request.session.pop('next', '/')
        if not next_path.startswith(('http://', 'https://')):
            base_url = settings.FRONTEND_URL.rstrip('/')
            path = next_path.lstrip('/')
            redirect_url = f"{base_url}/{path}"
        else:
            redirect_url = next_path
            
        error_url = f"{redirect_url}?error=auth_failed&message={str(e)}"
        if '?' in redirect_url:
            error_url = f"{redirect_url}&error=auth_failed&message={str(e)}"
            
        response = RedirectResponse(url=error_url)
        secure = True if (settings.API_BASE_URL and settings.API_BASE_URL.startswith("https://")) else False
        response.delete_cookie(key=f"oauth_state_{provider}", domain=".mentobe.co" if secure else None)
        return response
