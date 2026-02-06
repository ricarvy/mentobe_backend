from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.db_models import User, Payment, TarotInterpretation, AdminUser, SystemConfig, TarotSpreadCategory, TarotSpread
from app.dependencies import verify_password
from app.config import settings
from app.models import (
    UserResponse, SuccessResponse, ErrorResponse, LoginRequest,
    TarotCategoryCreate, TarotCategoryUpdate, TarotCategoryResponse,
    TarotSpreadCreate, TarotSpreadUpdate, TarotSpreadResponse
)
from app.services.stripe_service import fetch_price_details
from pydantic import BaseModel
from datetime import datetime
import asyncio

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

class SystemConfigUpdate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

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

# 0. System Configuration Management

@router.get("/configs", response_model=SuccessResponse)
async def list_configs(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    # Return all price related configs, populate with defaults from settings if not in DB
    keys = [
        "NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY",
        "NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY",
        "NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY",
        "NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY",
        "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_MONTHLY",
        "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_YEARLY"
    ]
    
    configs = []
    fetch_tasks = []
    
    for key in keys:
        db_config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        default_val = getattr(settings, key, "")
        val = db_config.value if db_config else default_val
        
        config_item = {
            "key": key,
            "value": val,
            "is_overridden": db_config is not None,
            "default_value": default_val,
            "price_details": None
        }
        configs.append(config_item)
        
        # Add task to fetch details if value exists
        if val:
            fetch_tasks.append(fetch_price_details(val))
        else:
            fetch_tasks.append(None) # Placeholder to keep index alignment
            
    # Fetch all prices in parallel
    # Filter out None tasks but keep track of indices or just use gather and handle None in result
    # Actually, asyncio.gather can handle coroutines. If I pass None it will fail.
    # So I need to wrap None in a dummy coroutine or filter.
    
    async def dummy_fetch(): return None
    
    real_tasks = []
    for t in fetch_tasks:
        if t:
            real_tasks.append(t)
        else:
            real_tasks.append(dummy_fetch())
            
    results = await asyncio.gather(*real_tasks)
    
    # Merge results back
    for i, res in enumerate(results):
        configs[i]["price_details"] = res
    
    return SuccessResponse(data=configs)

@router.post("/configs", response_model=SuccessResponse)
def update_config(config: SystemConfigUpdate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    db_config = db.query(SystemConfig).filter(SystemConfig.key == config.key).first()
    if not db_config:
        db_config = SystemConfig(key=config.key, value=config.value, description=config.description)
        db.add(db_config)
    else:
        db_config.value = config.value
        if config.description:
            db_config.description = config.description
    
    db.commit()
    return SuccessResponse(data={"message": "Config updated"})

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

from app.services.stripe_service import refund_payment

# 2. Payments Management

@router.get("/payments", response_model=SuccessResponse)
def list_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    data = []
    for p in payments:
        # Get user email
        user_email = "Unknown"
        if p.user:
            user_email = p.user.email

        data.append({
            "id": p.id,
            "user_id": p.user_id,
            "user_email": user_email,
            "amount_total": p.amount_total,
            "currency": p.currency,
            "status": p.status,
            "vip_level": p.vip_level,
            "created_at": p.created_at,
            "subscription_id": p.subscription_id,
            "invoice_id": p.invoice_id,
            "payment_intent_id": p.payment_intent_id,
            "stripe_session_id": p.stripe_session_id,
            "mode": p.mode
        })
    return SuccessResponse(data=data)

@router.post("/payments/{id}/refund", response_model=SuccessResponse)
async def refund_user_payment(id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status == "refunded":
        raise HTTPException(status_code=400, detail="Payment already refunded")
        
    if not payment.stripe_session_id and not payment.payment_intent_id:
        raise HTTPException(status_code=400, detail="No Stripe Session ID or Payment Intent ID for this payment")
        
    # Call Stripe Refund
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Pass payment_intent_id if available, otherwise session_id will be used to look it up
        result = await refund_payment(payment.stripe_session_id, payment.payment_intent_id)
        logger.info(f"Refund result for payment {id}: {result}")
        
        if not result.get("success"):
            error_msg = result.get("message")
            logger.error(f"Refund failed for payment {id}: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
            
        return SuccessResponse(message="Refund initiated successfully")
    except Exception as e:
        logger.error(f"Unexpected error during refund for payment {id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

# 5. Tarot Category Management

@router.post("/categories", response_model=SuccessResponse)
def create_category(category: TarotCategoryCreate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    db_category = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.slug == category.slug).first()
    if db_category:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")
    
    new_category = TarotSpreadCategory(
        slug=category.slug,
        name=category.name,
        name_en=category.name_en,
        name_jp=category.name_jp,
        description=category.description,
        description_en=category.description_en,
        description_jp=category.description_jp,
        sort_order=category.sort_order
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return SuccessResponse(data=TarotCategoryResponse.from_orm(new_category))

@router.get("/categories", response_model=SuccessResponse)
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    categories = db.query(TarotSpreadCategory).order_by(TarotSpreadCategory.sort_order.asc()).offset(skip).limit(limit).all()
    return SuccessResponse(data=[TarotCategoryResponse.from_orm(c) for c in categories])

@router.put("/categories/{id}", response_model=SuccessResponse)
def update_category(id: int, category: TarotCategoryUpdate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    db_category = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.id == id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category.slug:
        # Check uniqueness
        existing = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.slug == category.slug, TarotSpreadCategory.id != id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Slug already taken")
        db_category.slug = category.slug
    
    if category.name is not None:
        db_category.name = category.name
    if category.name_en is not None:
        db_category.name_en = category.name_en
    if category.name_jp is not None:
        db_category.name_jp = category.name_jp
    if category.description is not None:
        db_category.description = category.description
    if category.description_en is not None:
        db_category.description_en = category.description_en
    if category.description_jp is not None:
        db_category.description_jp = category.description_jp
    if category.sort_order is not None:
        db_category.sort_order = category.sort_order
    
    db.commit()
    db.refresh(db_category)
    return SuccessResponse(data=TarotCategoryResponse.from_orm(db_category))

@router.post("/categories/{id}/move", response_model=SuccessResponse)
def move_category(id: int, direction: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    """
    Move category up or down in sort order.
    direction: 'up' or 'down'
    """
    if direction not in ['up', 'down']:
        raise HTTPException(status_code=400, detail="Invalid direction. Use 'up' or 'down'")

    category = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    current_order = category.sort_order
    
    if direction == 'up':
        # Find the one immediately above (smaller sort_order)
        # We want the largest sort_order that is less than current_order
        target = db.query(TarotSpreadCategory)\
            .filter(TarotSpreadCategory.sort_order < current_order)\
            .order_by(TarotSpreadCategory.sort_order.desc())\
            .first()
    else: # down
        # Find the one immediately below (larger sort_order)
        # We want the smallest sort_order that is greater than current_order
        target = db.query(TarotSpreadCategory)\
            .filter(TarotSpreadCategory.sort_order > current_order)\
            .order_by(TarotSpreadCategory.sort_order.asc())\
            .first()
            
    if target:
        # Swap sort_order
        category.sort_order, target.sort_order = target.sort_order, category.sort_order
        db.commit()
        return SuccessResponse(message=f"Moved category {direction}")
    else:
        return SuccessResponse(message="Already at the edge", success=False)

@router.delete("/categories/{id}", response_model=SuccessResponse)
def delete_category(id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    db_category = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.id == id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(db_category)
    db.commit()
    return SuccessResponse(message="Category deleted")

# --- Spread Management ---

@router.post("/spreads", response_model=SuccessResponse)
def create_spread(spread: TarotSpreadCreate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    # Verify category exists
    category = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.id == spread.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")

    new_spread = TarotSpread(
        category_id=spread.category_id,
        name=spread.name,
        name_en=spread.name_en,
        name_jp=spread.name_jp,
        description=spread.description,
        description_en=spread.description_en,
        description_jp=spread.description_jp,
        card_count=spread.card_count,
        permission=spread.permission,
        sort_order=spread.sort_order
    )
    db.add(new_spread)
    db.commit()
    db.refresh(new_spread)
    return SuccessResponse(data=TarotSpreadResponse.from_orm(new_spread))

@router.get("/spreads", response_model=SuccessResponse)
def list_spreads(category_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    query = db.query(TarotSpread)
    if category_id:
        query = query.filter(TarotSpread.category_id == category_id)
    
    # Order by category sort order then spread sort order
    query = query.join(TarotSpread.category).order_by(TarotSpreadCategory.sort_order.asc(), TarotSpread.sort_order.asc())
    
    spreads = query.offset(skip).limit(limit).all()
    return SuccessResponse(data=[TarotSpreadResponse.from_orm(s) for s in spreads])

@router.put("/spreads/{id}", response_model=SuccessResponse)
def update_spread(id: int, spread: TarotSpreadUpdate, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    db_spread = db.query(TarotSpread).filter(TarotSpread.id == id).first()
    if not db_spread:
        raise HTTPException(status_code=404, detail="Spread not found")
    
    if spread.category_id is not None:
        category = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.id == spread.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")
    
    update_data = spread.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_spread, key, value)
    
    db.commit()
    db.refresh(db_spread)
    return SuccessResponse(data=TarotSpreadResponse.from_orm(db_spread))

@router.delete("/spreads/{id}", response_model=SuccessResponse)
def delete_spread(id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    db_spread = db.query(TarotSpread).filter(TarotSpread.id == id).first()
    if not db_spread:
        raise HTTPException(status_code=404, detail="Spread not found")
    
    db.delete(db_spread)
    db.commit()
    return SuccessResponse(message="Spread deleted successfully")

@router.post("/spreads/{id}/move", response_model=SuccessResponse)
def move_spread(id: int, direction: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    if direction not in ['up', 'down']:
        raise HTTPException(status_code=400, detail="Invalid direction")
    
    spread = db.query(TarotSpread).filter(TarotSpread.id == id).first()
    if not spread:
        raise HTTPException(status_code=404, detail="Spread not found")
    
    category_id = spread.category_id
    current_order = spread.sort_order
    
    if direction == 'up':
        target = db.query(TarotSpread)\
            .filter(TarotSpread.category_id == category_id, TarotSpread.sort_order < current_order)\
            .order_by(TarotSpread.sort_order.desc())\
            .first()
    else:
        target = db.query(TarotSpread)\
            .filter(TarotSpread.category_id == category_id, TarotSpread.sort_order > current_order)\
            .order_by(TarotSpread.sort_order.asc())\
            .first()
            
    if target:
        spread.sort_order, target.sort_order = target.sort_order, spread.sort_order
        db.commit()
        return SuccessResponse(message=f"Moved spread {direction}")
    else:
        return SuccessResponse(message="Already at the edge", success=False)
