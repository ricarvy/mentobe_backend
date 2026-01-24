from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
# from app.database import supabase # Removed
from app.database import get_db
from sqlalchemy.orm import Session
from app.db_models import User
from app.models import UserResponse
from app.config import settings
from passlib.context import CryptContext
import base64

security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    email = credentials.username
    password = credentials.password
    
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
            
    except Exception as e:
        # In case of DB error or other issues, fall back to unauthorized
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Basic"},
        )
