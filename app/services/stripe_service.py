import httpx
import logging
import stripe
from app.config import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

async def fetch_price_details(pid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch price details from Stripe API asynchronously.
    Returns a dict with id, unit_amount, amount (decimal), and currency.
    """
    if not pid:
        return None
        
    # If secret key is missing, return minimal info
    if not settings.STRIPE_SECRET_KEY:
        return {"id": pid, "amount": 0, "currency": "unknown", "status": "no_secret_key"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.STRIPE_API_BASE}/v1/prices/{pid}",
                headers={"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                unit_amount = data.get("unit_amount", 0)
                currency = data.get("currency", "usd")
                price_type = data.get("type", "one_time")
                recurring = data.get("recurring", {})
                interval = recurring.get("interval") if recurring else None
                
                # Extract multi-currency options
                currency_options = data.get("currency_options", {})
                currencies = []
                
                # If currency_options exists, use it to populate the list
                if currency_options:
                    for code, details in currency_options.items():
                        amt = details.get("unit_amount", 0)
                        currencies.append({
                            "currency": code.upper(),
                            "amount": amt / 100.0 if amt is not None else 0
                        })
                else:
                    # Fallback to single currency
                    currencies.append({
                        "currency": currency.upper(),
                        "amount": unit_amount / 100.0 if unit_amount else 0
                    })
                
                # Sort currencies by name for consistent display
                currencies.sort(key=lambda x: x["currency"])
                
                return {
                    "id": pid,
                    "unit_amount": unit_amount,
                    "amount": unit_amount / 100.0 if unit_amount else 0,
                    "currency": currency.upper(),
                    "currencies": currencies,
                    "type": price_type,
                    "interval": interval,
                    "status": "active"
                }
            else:
                logger.error(f"Stripe API error for {pid}: {response.status_code} {response.text}")
                return {
                    "id": pid, 
                    "amount": 0, 
                    "currency": "unknown", 
                    "status": "api_error",
                    "error_detail": f"Status: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Error fetching price {pid}: {e}")
    
    return {"id": pid, "amount": 0, "currency": "unknown", "error": "fetch_failed", "status": "error"}

async def refund_payment(session_id: str, payment_intent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Refund a payment by Stripe Session ID or Payment Intent ID.
    1. If payment_intent_id provided, use it.
    2. Else Retrieve Session to get Payment Intent
    3. Create Refund
    """
    if not settings.STRIPE_SECRET_KEY:
        return {"success": False, "message": "Stripe config missing"}
        
    try:
        # 1. Resolve Payment Intent
        if not payment_intent_id:
            session = stripe.checkout.Session.retrieve(
                session_id, 
                api_key=settings.STRIPE_SECRET_KEY
            )
            payment_intent_id = session.get("payment_intent")
            
            if not payment_intent_id:
                # Check if it's a subscription
                if session.get("mode") == "subscription":
                    # For subscriptions, we might need to refund the latest invoice
                    invoice_id = session.get("invoice")
                    if invoice_id:
                        invoice = stripe.Invoice.retrieve(invoice_id, api_key=settings.STRIPE_SECRET_KEY)
                        payment_intent_id = invoice.get("payment_intent")
                        logger.info(f"Retrieved Invoice {invoice_id}, Payment Intent: {payment_intent_id}")
            
        if not payment_intent_id:
            logger.warning(f"Payment Intent not found for session {session_id}")
            return {"success": False, "message": "Payment Intent not found (Invoice might be manually paid or $0)"}

        # 2. Create Refund
        logger.info(f"Initiating refund for Payment Intent: {payment_intent_id}")
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            api_key=settings.STRIPE_SECRET_KEY
        )
        
        return {"success": True, "refund_id": refund.id, "status": refund.status}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe Refund Error: {e}")
        return {"success": False, "message": str(e)}
    except Exception as e:
        logger.error(f"Refund Error: {e}")
        return {"success": False, "message": str(e)}

async def cancel_subscription(subscription_id: str) -> Dict[str, Any]:
    """
    Cancel a subscription (at period end).
    """
    if not settings.STRIPE_SECRET_KEY:
        return {"success": False, "message": "Stripe config missing"}
        
    try:
        # Update subscription to cancel at period end
        sub = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
            api_key=settings.STRIPE_SECRET_KEY
        )
        return {
            "success": True, 
            "status": sub.status, 
            "cancel_at_period_end": sub.cancel_at_period_end,
            "current_period_end": sub.current_period_end
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe Cancel Error: {e}")
        return {"success": False, "message": str(e)}
    except Exception as e:
        logger.error(f"Cancel Error: {e}")
        return {"success": False, "message": str(e)}
