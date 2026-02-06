import time
import json
import uuid
import hmac
import hashlib
import requests
import logging
from sqlalchemy import create_engine, text
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
BASE_URL = "http://localhost:8901"
WEBHOOK_URL = f"{BASE_URL}/api/stripe/webhook"
# Use the Test Mode Price ID from .env.local
PRICE_ID = settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY
WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET
DATABASE_URL = settings.DATABASE_URL

def get_db_engine():
    return create_engine(DATABASE_URL)

def create_test_user():
    engine = get_db_engine()
    user_id = str(uuid.uuid4())
    email = f"test_auto_{int(time.time())}@example.com"
    
    with engine.connect() as conn:
        try:
            # Create user
            stmt = text("INSERT INTO users (id, email, vip_level, is_active) VALUES (:id, :email, 0, 1)")
            conn.execute(stmt, {"id": user_id, "email": email})
            conn.commit()
            logger.info(f"Created test user: {email} (ID: {user_id})")
            return user_id, email
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise

def verify_user_vip(user_id, expected_level=1):
    engine = get_db_engine()
    max_retries = 5
    
    for i in range(max_retries):
        with engine.connect() as conn:
            result = conn.execute(text("SELECT vip_level, vip_expire_at FROM users WHERE id = :id"), {"id": user_id}).fetchone()
            if result and result[0] == expected_level:
                logger.info(f"✅ User VIP updated to level {result[0]}")
                logger.info(f"   Expire At: {result[1]}")
                
                # Check payment record
                payment = conn.execute(text("SELECT id, price_id, status FROM payments WHERE user_id = :id ORDER BY created_at DESC LIMIT 1"), {"id": user_id}).fetchone()
                if payment:
                    logger.info(f"✅ Payment record found: ID {payment[0]}, Status {payment[2]}")
                else:
                    logger.warning("❌ Payment record NOT found")
                return True
            else:
                current_level = result[0] if result else "None"
                logger.info(f"Waiting for update... (Attempt {i+1}/{max_retries}, Current Level: {current_level})")
                time.sleep(2)
    
    logger.error("❌ VIP update verification failed after retries")
    return False

def simulate_webhook(user_id):
    # Construct Stripe Event Payload
    # Note: Structure must match what Stripe sends.
    # The endpoint expects the full event object.
    
    session_id = f"cs_test_simulated_{int(time.time())}"
    
    event_payload = {
        "id": f"evt_test_{int(time.time())}",
        "object": "event",
        "api_version": "2022-11-15",
        "created": int(time.time()),
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "amount_total": 1000,
                "currency": "usd",
                "payment_status": "paid",
                "status": "complete",
                "client_reference_id": user_id,
                "metadata": {
                    "userId": user_id,
                    "priceId": PRICE_ID
                },
                # Sometimes subscription is present, sometimes not. For one-time payment it's null.
                # Assuming subscription logic relies on metadata or price lookup.
                "subscription": None 
            }
        }
    }
    
    payload_str = json.dumps(event_payload)
    timestamp = int(time.time())
    
    # Generate Signature
    signed_payload = f"{timestamp}.{payload_str}"
    signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": f"t={timestamp},v1={signature}"
    }
    
    logger.info(f"Sending Webhook to {WEBHOOK_URL}...")
    logger.info(f"Payload Price ID: {PRICE_ID}")
    
    try:
        response = requests.post(WEBHOOK_URL, data=payload_str, headers=headers)
        logger.info(f"Webhook Response: {response.status_code} {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Webhook Request Failed: {e}")
        return False

def main():
    logger.info("Starting Full Flow Test (Local Simulation with Online Config Keys)")
    
    # 1. Create User
    try:
        user_id, email = create_test_user()
    except Exception:
        return
    
    # 2. Simulate Login (Skipped, as we have user_id directly)
    # 3. Simulate Recharge (Webhook)
    if simulate_webhook(user_id):
        # 4. Verify DB
        verify_user_vip(user_id)
    else:
        logger.error("Webhook simulation failed, skipping verification")

if __name__ == "__main__":
    main()
