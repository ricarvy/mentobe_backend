from fastapi import APIRouter, HTTPException, Depends
from app.models import SuccessResponse, ErrorResponse
# from app.database import supabase # Removed
from app.database import get_db
from sqlalchemy.orm import Session
from app.db_models import User, AdminUser
from app.dependencies import get_password_hash
from app.config import settings
from datetime import datetime
import uuid

router = APIRouter(prefix="/system", tags=["system"])

@router.post("/create-admin", response_model=SuccessResponse)
def create_admin(db: Session = Depends(get_db)):
    """
    Create initial admin user if not exists
    """
    admin_username = "admin@mentobe.com" 
    password = "adminpassword" 
    
    try:
        # 1. Create in AdminUser table (for admin login)
        admin = db.query(AdminUser).filter(AdminUser.username == admin_username).first()
        if not admin:
            new_admin = AdminUser(
                username=admin_username,
                password=get_password_hash(password),
                role="admin"
            )
            db.add(new_admin)
            
        # 2. Create in User table (optional, but good for consistency if needed)
        user = db.query(User).filter(User.email == admin_username).first()
        if not user:
            new_user = User(
                email=admin_username,
                password=get_password_hash(password),
                username="Admin",
                is_active=True,
                created_at=datetime.now(),
                quota=999999,
                vip_level=99
            )
            db.add(new_user)
            
        db.commit()
        
        return SuccessResponse(data={"message": "Admin account created/verified"})
    except Exception as e:
        db.rollback()
        return ErrorResponse(success=False, error={"code": "CREATE_ERROR", "message": str(e)})
