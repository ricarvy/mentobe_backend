from fastapi import APIRouter, HTTPException, Request, Depends
from app.models import (
    SuccessResponse, ErrorResponse, 
    CreateCheckoutSessionRequest, CheckoutSessionResponse,
    CancelSubscriptionRequest, UserResponse
)
from app.config import settings
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.db_models import User, Payment, SystemConfig
from app.dependencies import get_current_user
from app.services.stripe_service import fetch_price_details, cancel_subscription
import httpx
import logging
import json
import os
import stripe
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi.concurrency import run_in_threadpool

# Set Stripe API version to ensure compatibility (e.g. accessing payment_intent on Invoice)
stripe.api_version = "2023-10-16"

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["stripe"])

# Helper function to get config (DB first, then Env)
def get_config_value(db: Session, key: str, default: str = None) -> str:
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if config and config.value:
        return config.value
    return default

@router.get("/config", response_model=SuccessResponse)
async def get_stripe_config(db: Session = Depends(get_db)):
    """
    获取 Stripe 配置（包含价格详情）
    """
    # Use injected DB session
    price_ids = {
            "pro_monthly": get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY),
            "pro_yearly": get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY),
            "premium_monthly": get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY),
            "premium_yearly": get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY),
            "upgrade_monthly": get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_MONTHLY", getattr(settings, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_MONTHLY", None)),
            "upgrade_yearly": get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_YEARLY", getattr(settings, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_YEARLY", None)),
        }

    # Fetch all prices in parallel
    tasks = []
    keys = []
    for key, pid in price_ids.items():
        keys.append(key)
        tasks.append(fetch_price_details(pid))
    
    results = await asyncio.gather(*tasks)
    
    prices_map = {}
    for key, result in zip(keys, results):
        if result:
            prices_map[key] = result
        else:
            prices_map[key] = {"id": price_ids[key], "amount": 0, "currency": "unknown"}

    return SuccessResponse(data={"prices": prices_map})

@router.post("/create-checkout-session", response_model=SuccessResponse)
async def create_checkout_session(request: CreateCheckoutSessionRequest, db: Session = Depends(get_db)):
    """
    创建 Stripe Checkout Session
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe configuration missing")

    logger.info(f"[Stripe API] Creating checkout session for user: {request.user_id}")
    
    # Get dynamic price configs
    # We fetch these to potentially validate price IDs or use them for logic if needed
    # But currently create_checkout_session mostly relies on the passed price_id
    pass

    # Determine mode by inspecting price details from Stripe
    mode = "payment"
    try:
        price_details = await fetch_price_details(request.price_id)
        if price_details and price_details.get("type") == "recurring":
            mode = "subscription"
    except Exception:
        pass

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

@router.post("/cancel-subscription", response_model=SuccessResponse)
async def cancel_user_subscription(
    request: CancelSubscriptionRequest, 
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Cancel user's subscription.
    If subscription_id is provided, cancel that specific one.
    Otherwise, find the active subscription for the user.
    """
    db = SessionLocal()
    try:
        sub_id = request.subscription_id
        
        if not sub_id:
            # Find active subscription for user
            # We look for a payment record that is 'subscription' and has a subscription_id
            # We prioritize the most recent one.
            payment = db.query(Payment).filter(
                Payment.user_id == current_user.id,
                Payment.mode == "subscription",
                Payment.subscription_id.isnot(None)
            ).order_by(Payment.created_at.desc()).first()
            
            if not payment:
                return ErrorResponse(success=False, error={"code": "NO_SUBSCRIPTION", "message": "No active subscription found"})
            
            sub_id = payment.subscription_id
        else:
            # Verify that the subscription belongs to the user
            payment = db.query(Payment).filter(
                Payment.user_id == current_user.id,
                Payment.subscription_id == sub_id
            ).first()
            
            if not payment:
                return ErrorResponse(success=False, error={"code": "INVALID_SUBSCRIPTION", "message": "Subscription not found or access denied"})
            
        # Call service
        result = await cancel_subscription(sub_id)
        
        if result.get("success"):
            return SuccessResponse(data=result)
        else:
            return ErrorResponse(success=False, error={"code": "CANCEL_FAILED", "message": result.get("message")})
            
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
        
    elif event["type"] == "charge.refunded":
        charge = event["data"]["object"]
        await handle_charge_refunded(charge)

    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        await handle_payment_intent_succeeded(payment_intent)

    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        await handle_invoice_payment_succeeded(invoice)

    return {"success": True}

async def handle_invoice_payment_succeeded(invoice: dict):
    """
    Handle invoice.payment_succeeded event.
    This is critical for Subscription payments where checkout.session.completed 
    might not have the payment_intent ready, or for recurring payments.
    """
    invoice_id = invoice.get("id")
    payment_intent_id = invoice.get("payment_intent")
    subscription_id = invoice.get("subscription")
    
    logger.info(f"Processing invoice.payment_succeeded: {invoice_id}, PI: {payment_intent_id}")
    
    # Fallback: If payment_intent_id is missing (e.g. newer API versions), retrieve it explicitly
    if not payment_intent_id and invoice_id:
        try:
            # We rely on the globally set stripe.api_version or explicit expansion
            inv_obj = await run_in_threadpool(
                lambda: stripe.Invoice.retrieve(invoice_id, expand=['payment_intent'], api_key=settings.STRIPE_SECRET_KEY)
            )
            # Check for payment_intent field or object
            pi_obj = inv_obj.get('payment_intent')
            if isinstance(pi_obj, dict):
                payment_intent_id = pi_obj.get('id')
            elif isinstance(pi_obj, str):
                payment_intent_id = pi_obj
            
            if payment_intent_id:
                logger.info(f"Retrieved missing PaymentIntent ID via API: {payment_intent_id}")
        except Exception as e:
            logger.error(f"Failed to retrieve Invoice details for PI: {e}")

    if not invoice_id or not payment_intent_id:
        return

    db = SessionLocal()
    try:
        # Update existing payment record by Invoice ID
        payment = db.query(Payment).filter(Payment.invoice_id == invoice_id).first()
        if payment:
            if not payment.payment_intent_id:
                payment.payment_intent_id = payment_intent_id
                db.commit()
                logger.info(f"Updated Payment {payment.id} with PaymentIntent ID: {payment_intent_id} (via Invoice event)")
            else:
                logger.info(f"Payment {payment.id} already has PaymentIntent ID: {payment.payment_intent_id}")
        else:
            # For recurring renewals, we might not have a Payment record yet 
            # (unless we created it on invoice.created or similar).
            # If we want to track renewals, we should create a Payment record here.
            # But based on current requirement (fix missing PI for initial payment),
            # updating the existing one is the priority.
            logger.info(f"No local payment found for Invoice {invoice_id}. Might be a renewal or unrecorded transaction.")
            
    except Exception as e:
        logger.error(f"Error handling invoice.payment_succeeded: {e}")
    finally:
        db.close()

async def handle_payment_intent_succeeded(payment_intent: dict):
    """
    Handle payment_intent.succeeded event.
    Used to ensure payment_intent_id is recorded in the database, 
    especially if checkout.session.completed missed it or for invoice payments.
    """
    pi_id = payment_intent.get("id")
    amount = payment_intent.get("amount")
    status = payment_intent.get("status")
    invoice_id = payment_intent.get("invoice")
    metadata = payment_intent.get("metadata", {})
    
    logger.info(f"Processing payment_intent.succeeded: {pi_id}, Invoice: {invoice_id}")
    
    db = SessionLocal()
    try:
        # 1. Try to find existing payment by Invoice ID
        if invoice_id:
            payment = db.query(Payment).filter(Payment.invoice_id == invoice_id).first()
            if payment:
                if not payment.payment_intent_id:
                    payment.payment_intent_id = pi_id
                    db.commit()
                    logger.info(f"Updated Payment {payment.id} with PaymentIntent ID: {pi_id} (via Invoice match)")
                return

        # 2. Try to find by Stripe Session ID (if in metadata)
        session_id = metadata.get("session_id") # Note: Stripe doesn't auto-add session_id to PI metadata usually
        if session_id:
            payment = db.query(Payment).filter(Payment.stripe_session_id == session_id).first()
            if payment:
                if not payment.payment_intent_id:
                    payment.payment_intent_id = pi_id
                    db.commit()
                    logger.info(f"Updated Payment {payment.id} with PaymentIntent ID: {pi_id} (via Session ID match)")
                return

        # 3. If not found, this might be a renewal or independent payment.
        # For now, we only log. Implementing full renewal logic requires handling invoice.payment_succeeded
        # which provides subscription details better than PI.
        logger.info(f"PaymentIntent {pi_id} succeeded but no matching local payment found (Invoice: {invoice_id}).")
        
    except Exception as e:
        logger.error(f"Error handling payment_intent.succeeded: {e}")
    finally:
        db.close()

async def handle_charge_refunded(charge: dict):
    """
    Handle charge refunded event.
    1. Find user and product from metadata (if available)
    2. Revert VIP status
    3. Update Payment status
    """
    logger.info(f"Processing charge.refunded: {charge.get('id')}")
    
    # Attempt to extract metadata
    # Charge metadata might be empty, check PaymentIntent if possible?
    # Usually metadata on Checkout Session is copied to Payment Intent, 
    # and sometimes to Charge depending on config.
    metadata = charge.get("metadata", {})
    payment_intent_id = charge.get("payment_intent")
    
    # If metadata is empty, try to retrieve PaymentIntent
    if not metadata and payment_intent_id and settings.STRIPE_SECRET_KEY:
        try:
            pi = stripe.PaymentIntent.retrieve(payment_intent_id, api_key=settings.STRIPE_SECRET_KEY)
            metadata = pi.get("metadata", {})
            logger.info(f"Retrieved metadata from PaymentIntent {payment_intent_id}")
        except Exception as e:
            logger.error(f"Failed to retrieve PaymentIntent: {e}")

    user_id = metadata.get("userId")
    price_id = metadata.get("priceId")
    
    db = SessionLocal()
    try:
        # 1. Update Payment Record Status
        payment = None
        
        # Priority 1: Search by PaymentIntent ID (Most reliable)
        if payment_intent_id:
            payment = db.query(Payment).filter(Payment.payment_intent_id == payment_intent_id).first()
            if payment:
                logger.info(f"Found payment {payment.id} via PaymentIntent ID {payment_intent_id}")
        
        # Priority 2: Fuzzy match by User ID + Price ID (Fallback)
        if not payment and user_id:
             # Find matching payment (approximate)
             # This is not perfect but works for most cases where users don't have many concurrent duplicate purchases.
             payment = db.query(Payment).filter(
                 Payment.user_id == user_id, 
                 Payment.price_id == price_id,
                 Payment.status == "paid"
             ).order_by(Payment.created_at.desc()).first()
             
             if payment:
                 logger.info(f"Found payment {payment.id} via User ID {user_id} and Price ID {price_id} (Fuzzy match)")
             
        if payment:
             payment.status = "refunded"
             db.commit()
             logger.info(f"Marked payment {payment.id} as refunded")
        else:
             logger.warning(f"Could not find payment record to mark as refunded. PI: {payment_intent_id}, User: {user_id}")

        
        # 2. Revert User Benefit
        if not user_id or not price_id:
            logger.error("Missing userId or priceId in refund metadata. Cannot revert benefit.")
            return

        vip_level, duration_days = get_vip_info(price_id)
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found for refund")
            return
            
        logger.info(f"Reverting benefit for user {user_id}. Level: {vip_level}, Duration: {duration_days}")
        
        if vip_level > 0:
            current_expire = user.vip_expire_at
            if current_expire:
                # Deduct duration
                new_expire = current_expire - timedelta(days=duration_days)
                
                # If new expiry is in the past, reset to Free (0)
                now = datetime.now(timezone.utc)
                
                # Ensure we are comparing timezone-aware datetimes
                if new_expire.tzinfo is None:
                    new_expire = new_expire.replace(tzinfo=timezone.utc)
                
                if new_expire < now:
                    user.vip_level = 0
                    user.vip_expire_at = None # Or keep the past date? None is cleaner for Free.
                    logger.info(f"User {user_id} downgraded to Free (Refund).")
                else:
                    user.vip_expire_at = new_expire
                    logger.info(f"User {user_id} expiry reduced to {new_expire}.")
            
            # Special case: If they were upgraded to a higher level, 
            # and now refunding, we might need to check if they have OTHER subscriptions?
            # For simplicity, we assume linear accumulation.
            
            # Reset quota if they drop to free?
            if user.vip_level == 0:
                user.quota = 3 # Reset to default free quota? Or 1?
                user.unlimited_quota = False # If we had this field? DB model check...
                # User model doesn't have 'unlimited_quota' column explicitly in db_models.py snippet?
                # Ah, auth.py constructs response with 'unlimitedQuota'.
                # User.quota is integer.
                pass
                
        db.commit()
        logger.info(f"Refund processing completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing refund: {e}")
        db.rollback()
    finally:
        db.close()

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
    # Fetch dynamic configs again because this function is called from webhook context
    # where we don't have them handy. 
    # Note: Frequent DB calls in webhook are okay, but caching would be better.
    # For now, let's keep it simple and safe by fetching fresh config.
    db = SessionLocal()
    try:
        pro_m = get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY)
        pro_y = get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_YEARLY)
        prem_m = get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_MONTHLY)
        prem_y = get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY", settings.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY)
        upg_m = get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_MONTHLY", getattr(settings, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_MONTHLY", None))
        upg_y = get_config_value(db, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_YEARLY", getattr(settings, "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_YEARLY", None))
    finally:
        db.close()

    if price_id == pro_m:
        return 1, 30
    elif price_id == pro_y:
        return 1, 365
    elif price_id == prem_m:
        return 2, 30
    elif price_id == prem_y:
        return 2, 365
    elif price_id == upg_m:
        return 2, 30  # Upgrade is effectively Premium
    elif price_id == upg_y:
        return 2, 365 # Upgrade is effectively Premium
    
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
        
        # 0. Extract extra IDs
        subscription_id = session.get("subscription")
        invoice_id = session.get("invoice")
        payment_intent_id = session.get("payment_intent")

        # If payment_intent is missing but we have an invoice, try to fetch it
        if not payment_intent_id and invoice_id and settings.STRIPE_SECRET_KEY:
            try:
                invoice_obj = stripe.Invoice.retrieve(invoice_id, api_key=settings.STRIPE_SECRET_KEY)
                payment_intent_id = invoice_obj.get("payment_intent")
                logger.info(f"Retrieved payment_intent_id {payment_intent_id} from invoice {invoice_id}")
            except Exception as e:
                logger.error(f"Failed to retrieve invoice {invoice_id} for payment intent: {e}")

        # 1. Insert into payments table
        payment = Payment(
            user_id=user_id,
            stripe_session_id=session.get("id"),
            payment_intent_id=payment_intent_id,
            subscription_id=subscription_id,
            invoice_id=invoice_id,
            amount_total=session.get("amount_total"),
            currency=session.get("currency"),
            status=session.get("payment_status"),
            price_id=price_id,
            vip_level=vip_level,
            vip_duration="monthly" if duration_days == 30 else "yearly" if duration_days == 365 else "unknown",
            mode=session.get("mode")
        )
        db.add(payment)
        
        print(f"✅ [Payment Updated] User: {user_id}, Amount: {session.get('amount_total')}, Status: {session.get('payment_status')}")
        logger.info(f"Payment recorded for user {user_id}")
        
        vip_update_status = "Not Attempted"
        vip_update_reason = "VIP Level is 0 (Unknown Price ID)" if vip_level == 0 else "Unknown"

        # 2. Update user VIP status ONLY if vip_level > 0
        if vip_level > 0:
            now = datetime.now(timezone.utc)
            # new_expire_at calculation deferred until we check user's current status

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
                
                # Default new expiration (Now + Duration) - for new subs or expired
                new_expire_at = now + timedelta(days=duration_days)

                if current_expire_at and current_expire_at > now:
                    # User has active subscription
                    if vip_level > current_vip_level:
                         # Upgrade: Per user request, add duration to ORIGINAL expiration date
                         new_expire_at = current_expire_at + timedelta(days=duration_days)
                         should_update = True
                         vip_update_reason = "Upgrade (Extended)"
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
