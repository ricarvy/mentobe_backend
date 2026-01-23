from fastapi import APIRouter, HTTPException, Depends
from app.models import SuccessResponse, ErrorResponse
# from app.database import supabase # Removed
from app.database import get_db
from sqlalchemy.orm import Session
from app.db_models import User
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
    email = "admin@mentobe.com" # Or from settings
    password = "adminpassword" # Should be strong and from env
    
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return SuccessResponse(data={"message": "Admin already exists"})
            
        new_user = User(
            email=email,
            password=get_password_hash(password),
            username="Admin",
            is_active=True,
            created_at=datetime.now(),
            quota=999999,
            vip_level=99
        )
        db.add(new_user)
        db.commit()
        
        return SuccessResponse(data={"message": "Admin created"})
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "CREATE_ERROR", "message": str(e)})
