from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
# from app.database import supabase # Removed
from app.database import get_db
from sqlalchemy.orm import Session
from app.db_models import User
from app.models import UserResponse
from app.config import settings
from passlib.context import CryptContext
import base64
from typing import Optional
from app.utils.security import decode_access_token

security = HTTPBasic(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(
    basic_creds: Optional[HTTPBasicCredentials] = Depends(security),
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # 1. Try Bearer Token (JWT)
    if token:
        payload = decode_access_token(token)
        if payload:
            email = payload.get("sub")
            if email:
                # Check demo account via token (if we ever issue tokens for demo user)
                if settings.DEMO_ACCOUNT_ENABLED and email == settings.DEMO_ACCOUNT_EMAIL:
                     return UserResponse(
                        id="demo-user-id",
                        username="Demo User",
                        email=email,
                        isActive=True,
                        isDemo=True,
                        unlimitedQuota=True
                    )
                
                # Check DB
                user = db.query(User).filter(User.email == email).first()
                if user:
                    return UserResponse(
                        id=str(user.id),
                        username=user.username,
                        email=user.email,
                        isActive=user.is_active,
                        isDemo=False,
                        unlimitedQuota=True if user.vip_level and user.vip_level > 0 else False,
                        vipLevel=user.vip_level,
                        vipExpireAt=user.vip_expire_at.isoformat() if user.vip_expire_at else None
                    )
        
        # If token provided but invalid or user not found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Try Basic Auth
    if basic_creds:
        email = basic_creds.username
        password = basic_creds.password
        
        # Check for demo account
        if settings.DEMO_ACCOUNT_ENABLED and email == settings.DEMO_ACCOUNT_EMAIL:
            if password == settings.DEMO_ACCOUNT_PASSWORD:
                return UserResponse(
                    id="demo-user-id",
                    username="Demo User",
                    email=email,
                    isActive=True,
                    isDemo=True,
                    unlimitedQuota=True
                )
        
        # Check database for regular user
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
            
            if not verify_password(password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
                
            return UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                isActive=user.is_active,
                isDemo=False,
                unlimitedQuota=True if user.vip_level and user.vip_level > 0 else False,
                vipLevel=user.vip_level,
                vipExpireAt=user.vip_expire_at.isoformat() if user.vip_expire_at else None
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Auth Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Basic"},
            )

    # 3. No credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Basic"},
    )
