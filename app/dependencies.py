from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.database import supabase
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

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
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
        response = supabase.table("users").select("*").eq("email", email).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        user_data = response.data[0]
        if not verify_password(password, user_data["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
            
        return UserResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            isActive=user_data.get("is_active", True),
            isDemo=False,
            unlimitedQuota=False
        )
            
    except Exception as e:
        # In case of DB error or other issues, fall back to unauthorized
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Basic"},
        )
