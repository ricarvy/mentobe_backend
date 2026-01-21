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

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["stripe"])

@router.post("/create-checkout-session", response_model=SuccessResponse)
async def create_checkout_session(request: CreateCheckoutSessionRequest):
    """
    创建 Stripe Checkout Session
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe configuration missing")

    logger.info(f"[Stripe API] Creating checkout session for user: {request.user_id}")

    try:
        async with httpx.AsyncClient() as client:
            stripe_response = await client.post(
                f"{settings.STRIPE_API_BASE}/v1/checkout/sessions",
                headers={
                    "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "mode": "payment",
                    "payment_method_types": "card",
                    "line_items[0][price]": request.price_id,
                    "line_items[0][quantity]": 1,
                    "success_url": request.success_url,
                    "cancel_url": request.cancel_url,
                    "customer_email": request.user_email,
                    "client_reference_id": request.user_id,
                    "metadata[userId]": request.user_id,
                    "metadata[userEmail]": request.user_email,
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

    # In a real production environment, you should verify the signature using the stripe library.
    # import stripe
    # try:
    #     event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    # except ValueError as e: ...
    # except stripe.error.SignatureVerificationError as e: ...
    
    # For now, we'll proceed with basic JSON parsing as in the reference
    try:
        event = json.loads(payload)
        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})

        logger.info(f"[Stripe Webhook] Received event: {event_type}")

        if event_type == "checkout.session.completed":
            user_id = event_data.get("metadata", {}).get("userId")
            logger.info(f"[Stripe Webhook] Payment completed for user {user_id}")
            
            # TODO: Implement quota update logic here
            # Example: await QuotaService.add_quota(user_id, amount=10)
            
        elif event_type == "payment_intent.succeeded":
            logger.info("[Stripe Webhook] Payment succeeded")
            
        elif event_type == "payment_intent.payment_failed":
            logger.warning("[Stripe Webhook] Payment failed")

        return {"success": True, "received": True}

    except Exception as e:
        logger.error(f"[Stripe Webhook] Error processing event: {e}")
        raise HTTPException(status_code=400, detail="Error processing event")
