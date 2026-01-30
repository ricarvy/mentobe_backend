from fastapi import APIRouter, HTTPException, Request, Depends
from app.models import (
    SuccessResponse, ErrorResponse, 
    CreateCheckoutSessionRequest, CheckoutSessionResponse
)
from app.config import settings
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.db_models import User, Payment
import httpx
import logging
import json
import os
import stripe
from datetime import datetime, timedelta, timezone
from fastapi.concurrency import run_in_threadpool

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["stripe"])

@router.get("/config", response_model=SuccessResponse)
async def get_stripe_config():
    """
    获取 Stripe 配置（公开价格 ID）
    """
    return SuccessResponse(data={
        "prices": {
            "pro_monthly": settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY,
            "pro_yearly": settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY,
            "premium_monthly": settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY,
            "premium_yearly": settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY,
        }
    })

@router.post("/create-checkout-session", response_model=SuccessResponse)
async def create_checkout_session(request: CreateCheckoutSessionRequest):
    """
    创建 Stripe Checkout Session
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe configuration missing")

    logger.info(f"[Stripe API] Creating checkout session for user: {request.user_id}")

    # Determine mode based on price_id
    mode = "payment"
    subscription_prices = [
        settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY,
        settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY,
        settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY,
        settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY
    ]
    if request.price_id in subscription_prices:
        mode = "subscription"

    try:
        async with httpx.AsyncClient() as client:
            stripe_response = await client.post(
                f"{settings.STRIPE_API_BASE}/v1/checkout/sessions",
                headers={
                    "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "mode": mode,
                    "payment_method_types[0]": "card",
                    "line_items[0][price]": request.price_id,
                    "line_items[0][quantity]": 1,
                    "success_url": request.success_url,
                    "cancel_url": request.cancel_url,
                    "customer_email": request.user_email,
                    "client_reference_id": request.user_id,
                    "metadata[userId]": request.user_id,
                    "metadata[userEmail]": request.user_email,
                    "metadata[priceId]": request.price_id,
                },
                timeout=30.0,
            )

        stripe_data = stripe_response.json()

        if stripe_response.status_code != 200:
            error_detail = stripe_data.get("error", {})
            logger.error(f"[Stripe API] Error: {error_detail}")
            return ErrorResponse(success=False, error={
                "code": error_detail.get("code", "STRIPE_API_ERROR"),
                "message": error_detail.get("message", "Stripe API failed"),
                "details": str(error_detail)
            })

        session_id = stripe_data.get("id")
        checkout_url = stripe_data.get("url")

        logger.info(f"[Stripe API] Session created: {session_id}")

        return SuccessResponse(
            data=CheckoutSessionResponse(
                sessionId=session_id,
                url=checkout_url
            )
        )

    except Exception as e:
        logger.error(f"[Stripe API] Unexpected error: {e}")
        return ErrorResponse(success=False, error={
            "code": "INTERNAL_ERROR",
            "message": str(e)
        })

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe Webhook Endpoint
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured")
        return {"success": False, "message": "Webhook secret not configured"}

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Webhook error: Invalid payload: {e}")
        return {"success": False, "message": "Invalid payload"}
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook error: Invalid signature: {e}")
        return {"success": False, "message": "Invalid signature"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session)

    return {"success": True}

@router.get("/webhook")
async def stripe_webhook_get():
    """
    Stripe Webhook GET Endpoint
    To prevent 405 Method Not Allowed error when accessing via browser
    """
    return {"message": "This is a Stripe webhook endpoint. Please use POST."}

def get_vip_info(price_id: str):
    """
    Helper to get VIP level and duration based on price_id
    """
    if price_id == settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY:
        return 1, 30
    elif price_id == settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY:
        return 1, 365
    elif price_id == settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY:
        return 2, 30
    elif price_id == settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY:
        return 2, 365
    
    logger.warning(f"Unknown price_id: {price_id}")
    return 0, 0

def _handle_checkout_completed_sync(session: dict):
    """
    Sync handler for checkout completion
    """
    # Prefer client_reference_id, fallback to metadata.userId
    user_id = session.get("client_reference_id") or session.get("metadata", {}).get("userId")
    # Try to get price_id from metadata
    price_id = session.get("metadata", {}).get("priceId")
    
    if not user_id or not price_id:
        logger.error(f"Missing user_id or price_id in session. user_id: {user_id}, price_id: {price_id}, metadata: {session.get('metadata')}")
        return

    vip_level, duration_days = get_vip_info(price_id)
    
    if vip_level == 0:
        logger.error(f"Invalid VIP level 0 for price_id: {price_id}. Configured prices: ProM={settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY}, ProY={settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY}, PreM={settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY}, PreY={settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY}")
        # We still record the payment for audit, but mark as unknown/failed logic maybe?
    
    db = SessionLocal()
    try:
        # 1. Insert into payments table
        payment = Payment(
            user_id=user_id,
            stripe_session_id=session.get("id"),
            amount_total=session.get("amount_total"),
            currency=session.get("currency"),
            status=session.get("payment_status"),
            price_id=price_id,
            vip_level=vip_level,
            vip_duration="monthly" if duration_days == 30 else "yearly" if duration_days == 365 else "unknown"
        )
        db.add(payment)
        
        print(f"✅ [Payment Updated] User: {user_id}, Amount: {session.get('amount_total')}, Status: {session.get('payment_status')}")
        logger.info(f"Payment recorded for user {user_id}")
        
        # 2. Update user VIP status ONLY if vip_level > 0
        if vip_level > 0:
            now = datetime.now(timezone.utc)
            new_expire_at = now + timedelta(days=duration_days)

            user = db.query(User).filter(User.id == user_id).first()
            if user:
                current_vip_level = user.vip_level or 0
                current_expire_at = user.vip_expire_at

                # Logic for VIP update:
                # 1. If upgrading (higher level), overwrite level and expiry (restart duration)
                # 2. If same level, extend expiry
                # 3. If downgrading (lower level), this logic might need business rule clarification, 
                #    but typically we shouldn't downgrade until current high-tier expires. 
                #    For now, we'll assume new purchase overrides if it's an upgrade or same level.
                
                should_update = False
                
                if current_expire_at:
                    if current_expire_at.tzinfo is None:
                        current_expire_at = current_expire_at.replace(tzinfo=timezone.utc)
                
                if current_expire_at and current_expire_at > now:
                    # User has active subscription
                    if vip_level > current_vip_level:
                         # Upgrade: Overwrite level and reset time (or add time? usually reset for upgrade)
                         # Let's say upgrade starts fresh from today
                         should_update = True
                    elif vip_level == current_vip_level:
                         # Same level: Extend
                         new_expire_at = current_expire_at + timedelta(days=duration_days)
                         should_update = True
                    else:
                         # Downgrade attempt while active (e.g. bought Basic while Pro is active)
                         # Business decision: Do we stack? Do we ignore?
                         # For now: Log warning and maybe extend if we want to be generous, 
                         # or just let them have the lower tier after the higher one expires (complex).
                         # Simple approach: If new level is lower, we DON'T downgrade active high-tier user.
                         logger.warning(f"User {user_id} bought lower tier {vip_level} while having active tier {current_vip_level}. Ignoring downgrade.")
                         should_update = False 
                else:
                    # No active subscription or expired
                    should_update = True

                if should_update:
                    user.vip_level = vip_level
                    user.vip_expire_at = new_expire_at
                    user.quota = 999999
                    db.add(user)
                    print(f"✅ [User Updated] User: {user_id}, New Level: {vip_level}, Expires: {new_expire_at}, Quota: 999999")
                    logger.info(f"User {user_id} VIP updated to level {vip_level}, expires {new_expire_at}")

            else:
                logger.error(f"User {user_id} not found in database")
        
        db.commit()

    except Exception as e:
        logger.error(f"Failed to handle checkout completion: {e}")
        db.rollback()
    finally:
        db.close()

async def handle_checkout_completed(session: dict):
    await run_in_threadpool(_handle_checkout_completed_sync, session)
