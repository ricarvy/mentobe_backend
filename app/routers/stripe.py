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

    # Append session_id to success_url if not present
    success_url = request.success_url
    if "{CHECKOUT_SESSION_ID}" not in success_url:
        separator = "&" if "?" in success_url else "?"
        success_url = f"{success_url}{separator}session_id={{CHECKOUT_SESSION_ID}}"

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
                    "success_url": success_url,
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

@router.get("/payment-status/{session_id}")
async def check_payment_status(session_id: str):
    """
    Check payment status by Stripe Session ID.
    Returns:
    - completed: Payment processed and recorded in DB.
    - waiting_for_webhook: Payment successful at Stripe but DB not updated yet.
    - pending: Payment not yet completed.
    - failed: Payment failed or expired.
    - not_found: Session ID not found.
    """
    db = SessionLocal()
    try:
        # 1. Check local DB
        payment = db.query(Payment).filter(Payment.stripe_session_id == session_id).first()
        if payment:
            return {"status": "completed", "vip_level": payment.vip_level}
        
        # 2. Check Stripe API
        if not settings.STRIPE_SECRET_KEY:
             return {"status": "unknown", "message": "Stripe key not configured"}

        try:
            session = stripe.checkout.Session.retrieve(session_id, api_key=settings.STRIPE_SECRET_KEY)
            payment_status = session.get("payment_status")
            status = session.get("status")
            
            if payment_status == "paid":
                # Paid but not in DB yet -> Trigger manual update
                logger.info(f"Payment {session_id} verified via API. Triggering manual sync.")
                try:
                    await handle_checkout_completed(session)
                    return {"status": "completed", "source": "api_verification"}
                except Exception as e:
                    logger.error(f"Manual sync failed: {e}")
                    return {"status": "waiting_for_webhook", "error": str(e)}
            elif status == "open":
                return {"status": "pending"}
            elif status == "expired":
                return {"status": "failed"}
            else:
                return {"status": session.get("status")}
                
        except stripe.error.InvalidRequestError:
            return {"status": "not_found"}
            
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

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
        # Log the raw payload for debugging (truncated)
        logger.info(f"Webhook received. Header: {sig_header[:20]}...")
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        logger.info(f"Webhook signature verified. Event type: {event['type']}")
        
    except ValueError as e:
        logger.error(f"Webhook error: Invalid payload: {e}")
        return {"success": False, "message": "Invalid payload"}
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"CRITICAL: Webhook Signature Verification Failed! Check your STRIPE_WEBHOOK_SECRET in .env vs Stripe Dashboard/CLI. Error: {e}")
        # Log which secret was used (masked)
        secret_masked = webhook_secret[:5] + "..." + webhook_secret[-5:] if webhook_secret else "None"
        logger.error(f"Used Secret: {secret_masked}")
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
    
    db = SessionLocal()
    try:
        # Fallback: Try to find user by email if user_id is missing
        if not user_id:
            customer_email = session.get("customer_details", {}).get("email") or session.get("customer_email")
            if customer_email:
                logger.info(f"Looking up user by email: {customer_email}")
                user = db.query(User).filter(User.email == customer_email).first()
                if user:
                    user_id = user.id
                    logger.info(f"Found user {user_id} by email {customer_email}")
                else:
                    logger.warning(f"User with email {customer_email} not found")
        
        # Fallback: Try to fetch price_id from line_items if missing
        if not price_id:
            logger.info("price_id missing from metadata, attempting to retrieve from line_items...")
            try:
                # We need to retrieve the session again with line_items expanded
                # Check if line_items are already in the session object (sometimes they are)
                # But typically 'checkout.session.completed' does NOT contain line_items unless expanded.
                # However, we can use the stripe library to retrieve it.
                if settings.STRIPE_SECRET_KEY:
                    expanded_session = stripe.checkout.Session.retrieve(
                        session["id"],
                        expand=["line_items"],
                        api_key=settings.STRIPE_SECRET_KEY
                    )
                    if expanded_session.line_items and expanded_session.line_items.data:
                        price_id = expanded_session.line_items.data[0].price.id
                        logger.info(f"Retrieved price_id from line_items: {price_id}")
            except Exception as e:
                logger.error(f"Failed to retrieve line_items from Stripe: {e}")

        if not user_id or not price_id:
            msg = f"CRITICAL: Payment successful but failed to identify User or Product. Manual intervention required. Session ID: {session.get('id')}, Email: {session.get('customer_details', {}).get('email')}, Metadata: {session.get('metadata')}. Action: Payment successful but database not updated. Please contact administrator."
            logger.error(msg)
            return

        vip_level, duration_days = get_vip_info(price_id)
        
        if vip_level == 0:
            msg = f"CRITICAL: Payment successful for Price ID {price_id} but it does not map to a valid VIP level. Check Stripe Price IDs in config. Session ID: {session.get('id')}. Action: Payment successful but database not updated. Please contact administrator."
            logger.error(msg)
            # We still record the payment for audit, but mark as unknown/failed logic maybe?
        
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
        
        vip_update_status = "Not Attempted"
        vip_update_reason = "VIP Level is 0 (Unknown Price ID)" if vip_level == 0 else "Unknown"

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
                         vip_update_reason = "Upgrade"
                    elif vip_level == current_vip_level:
                         # Same level: Extend
                         new_expire_at = current_expire_at + timedelta(days=duration_days)
                         should_update = True
                         vip_update_reason = "Extension"
                    else:
                         # Downgrade attempt while active (e.g. bought Basic while Pro is active)
                         # Business decision: Do we stack? Do we ignore?
                         # For now: Log warning and maybe extend if we want to be generous, 
                         # or just let them have the lower tier after the higher one expires (complex).
                         # Simple approach: If new level is lower, we DON'T downgrade active high-tier user.
                         msg = f"ALERT: User {user_id} purchased lower tier {vip_level} (Current: {current_vip_level}). VIP update skipped to prevent downgrade. Action: Payment successful but database not updated. Please contact administrator if this is an error."
                         logger.warning(msg)
                         should_update = False 
                         vip_update_status = "Skipped"
                         vip_update_reason = f"Downgrade prevention (Current: {current_vip_level}, New: {vip_level})"
                else:
                    # No active subscription or expired
                    should_update = True
                    vip_update_reason = "New Subscription"

                if should_update:
                    user.vip_level = vip_level
                    user.vip_expire_at = new_expire_at
                    user.quota = 999999
                    db.add(user)
                    print(f"✅ [User Updated] User: {user_id}, New Level: {vip_level}, Expires: {new_expire_at}, Quota: 999999")
                    logger.info(f"User {user_id} VIP updated to level {vip_level}, expires {new_expire_at}")
                    vip_update_status = "Success"

            else:
                msg = f"CRITICAL: Payment successful for User ID {user_id} but user record NOT FOUND in database. Payment recorded but VIP not updated. Action: Payment successful but database not updated. Please contact administrator."
                logger.error(msg)
                vip_update_status = "Failed"
                vip_update_reason = "User Not Found"
        
        db.commit()
        
        # --- Final Verification Log ---
        try:
            db.refresh(payment)
            log_msg = f"[Payment Verification] PaymentID: {payment.id}, Status: {payment.status}, VIP Update: {vip_update_status} ({vip_update_reason})"
            if vip_update_status == "Success":
                 logger.info(f"✅ NORMAL: {log_msg}")
            else:
                 logger.critical(f"❌ ABNORMAL: {log_msg}. Action: Check database consistency.")
        except Exception as verify_e:
             logger.error(f"Error during payment verification logging: {verify_e}")
        # ------------------------------

    except Exception as e:
        msg = f"CRITICAL: Unexpected error processing payment for User {user_id if 'user_id' in locals() else 'Unknown'}: {e}. Action: Payment successful but database not updated. Please contact administrator."
        logger.error(msg, exc_info=True)
        db.rollback()
    finally:
        db.close()

async def handle_checkout_completed(session: dict):
    await run_in_threadpool(_handle_checkout_completed_sync, session)
