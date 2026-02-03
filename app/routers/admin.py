from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.db_models import User, Payment, TarotInterpretation, AdminUser
from app.dependencies import verify_password
from app.models import UserResponse, SuccessResponse, ErrorResponse, LoginRequest
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])

security = HTTPBasic()

# --- Dependencies ---

def get_current_admin(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)) -> AdminUser:
    admin = db.query(AdminUser).filter(AdminUser.username == credentials.username).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not verify_password(credentials.password, admin.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return admin

# --- Schemas for Admin ---

class AdminUserUpdate(BaseModel):
    quota: Optional[int] = None
    vip_level: Optional[int] = None
    vip_expire_at: Optional[datetime] = None
    password: Optional[str] = None

class AdminPaymentResponse(BaseModel):
    id: int
    user_id: str
    amount_total: Optional[int]
    status: Optional[str]
    created_at: datetime

class AdminInterpretationResponse(BaseModel):
    id: int
    user_id: str
    question: Optional[str]
    created_at: datetime

# --- Routes ---

@router.post("/login", response_model=SuccessResponse)
def admin_login(request: LoginRequest, db: Session = Depends(get_db)):
    # Treat email as username
    admin = db.query(AdminUser).filter(AdminUser.username == request.email).first()
    if not admin or not verify_password(request.password, admin.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return SuccessResponse(data={
        "username": admin.username,
        "role": admin.role
    })

# 1. Users Management

@router.get("/users", response_model=SuccessResponse)
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    users = db.query(User).offset(skip).limit(limit).all()
    data = []
    for u in users:
        data.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "quota": u.quota,
            "vip_level": u.vip_level,
            "vip_expire_at": u.vip_expire_at,
            "created_at": u.created_at,
            "last_active": None # Add if tracked
        })
    return SuccessResponse(data=data)

@router.put("/users/{user_id}", response_model=SuccessResponse)
def update_user(user_id: str, update: AdminUserUpdate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if update.quota is not None:
        user.quota = update.quota
    if update.vip_level is not None:
        user.vip_level = update.vip_level
    if update.vip_expire_at is not None:
        user.vip_expire_at = update.vip_expire_at
    # Password update logic could go here if needed (hashing required)
        
    db.commit()
    db.refresh(user)
    return SuccessResponse(data={"message": "User updated"})

@router.delete("/users/{user_id}", response_model=SuccessResponse)
def delete_user(user_id: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cascade delete is usually handled by DB, but SQLAlchemy relationship cascade can be set.
    # For now, let's assume DB handles it or we manually delete related.
    # Manually deleting related items just in case
    db.query(Payment).filter(Payment.user_id == user_id).delete()
    db.query(TarotInterpretation).filter(TarotInterpretation.user_id == user_id).delete()
    
    db.delete(user)
    db.commit()
    return SuccessResponse(data={"message": "User deleted"})

# 2. Payments Management

@router.get("/payments", response_model=SuccessResponse)
def list_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    data = []
    for p in payments:
        data.append({
            "id": p.id,
            "user_id": p.user_id,
            "amount_total": p.amount_total,
            "status": p.status,
            "created_at": p.created_at
        })
    return SuccessResponse(data=data)

# 3. Interpretations Management

@router.get("/interpretations", response_model=SuccessResponse)
def list_interpretations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    items = db.query(TarotInterpretation).order_by(TarotInterpretation.created_at.desc()).offset(skip).limit(limit).all()
    data = []
    for i in items:
        data.append({
            "id": i.id,
            "user_id": i.user_id,
            "question": i.question,
            "spread_type": i.spread_type,
            "created_at": i.created_at
        })
    return SuccessResponse(data=data)

@router.delete("/interpretations/{id}", response_model=SuccessResponse)
def delete_interpretation(id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    item = db.query(TarotInterpretation).filter(TarotInterpretation.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return SuccessResponse(data={"message": "Interpretation deleted"})
