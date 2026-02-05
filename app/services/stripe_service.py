import httpx
import logging
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
                return {
                    "id": pid,
                    "unit_amount": unit_amount,
                    "amount": unit_amount / 100.0 if unit_amount else 0,
                    "currency": currency.upper(),
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
