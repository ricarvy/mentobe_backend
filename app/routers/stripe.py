from fastapi import APIRouter, HTTPException, Request, Depends
from app.models import (
    SuccessResponse, ErrorResponse, 
    CreateCheckoutSessionRequest, CheckoutSessionResponse
)
from app.config import settings
from app.database import supabase
import httpx
import logging
import json
import os
import stripe
from datetime import datetime, timedelta, timezone

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
    return 0, 0

async def handle_checkout_completed(session: dict):
    """
    Handle successful checkout session
    """
    user_id = session.get("client_reference_id")
    # Try to get price_id from metadata
    price_id = session.get("metadata", {}).get("priceId")
    
    if not user_id or not price_id:
        logger.error("Missing user_id or price_id in session metadata")
        return

    vip_level, duration_days = get_vip_info(price_id)
    
    # 1. Insert into payments table
    payment_data = {
        "user_id": user_id,
        "stripe_session_id": session.get("id"),
        "amount_total": session.get("amount_total"),
        "currency": session.get("currency"),
        "status": session.get("payment_status"),
        "price_id": price_id,
        "vip_level": vip_level,
        "vip_duration": "monthly" if duration_days == 30 else "yearly" if duration_days == 365 else "unknown"
    }
    
    try:
        supabase.table("payments").insert(payment_data).execute()
        print(f"✅ [Payment Updated] User: {user_id}, Amount: {payment_data['amount_total']}, Status: {payment_data['status']}")
        logger.info(f"Payment recorded for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to record payment: {e}")

    # 2. Update user VIP status
    now = datetime.now(timezone.utc)
    new_expire_at = now + timedelta(days=duration_days)

    try:
        current_user_resp = supabase.table("users").select("vip_expire_at, vip_level").eq("id", user_id).execute()
        if current_user_resp.data:
            current_user = current_user_resp.data[0]
            current_expire_at_str = current_user.get("vip_expire_at")
            current_vip_level = current_user.get("vip_level", 0)

            if current_expire_at_str:
                # Handle potential Z suffix or offset
                current_expire_at_str = current_expire_at_str.replace('Z', '+00:00')
                try:
                    current_expire_at = datetime.fromisoformat(current_expire_at_str)
                    # If same level and not expired, extend
                    if current_vip_level == vip_level and current_expire_at > now:
                        new_expire_at = current_expire_at + timedelta(days=duration_days)
                except ValueError:
                    pass # Invalid date format, stick to now + duration

        update_data = {
            "vip_level": vip_level,
            "vip_expire_at": new_expire_at.isoformat(),
            "quota": 999999
        }

        supabase.table("users").update(update_data).eq("id", user_id).execute()
        print(f"✅ [User Updated] User: {user_id}, New Level: {vip_level}, Expires: {new_expire_at}, Quota: 999999")
        logger.info(f"User {user_id} VIP updated to level {vip_level}, expires {new_expire_at}")
    except Exception as e:
        logger.error(f"Failed to update user VIP status: {e}")
