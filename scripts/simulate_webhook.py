import httpx
import asyncio
import json
import time
import os
import stripe
import hmac
import hashlib
from dotenv import load_dotenv

# Load env to get secret
load_dotenv()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Configuration
API_URL = "http://localhost:8000/api/stripe/webhook"
# Demo user UUID as defined in auth.py
USER_ID = "00000000-0000-0000-0000-000000000000"

async def main():
    if not STRIPE_WEBHOOK_SECRET:
        print("Error: STRIPE_WEBHOOK_SECRET not found in .env")
        return

    async with httpx.AsyncClient() as client:
        # 1. Login to ensure Demo User exists in DB
        print("Logging in to ensure Demo User exists...")
        try:
            login_resp = await client.post("http://localhost:8000/api/auth/login", json={
                "email": "demo@mentobai.com",
                "password": "Demo123!"
            })
            print(f"Login status: {login_resp.status_code}")
            if login_resp.status_code != 200:
                print("Login failed, aborting.")
                return
        except Exception as e:
            print(f"Failed to connect to backend: {e}")
            return

        # 2. Fetch config to get valid price IDs
        print("Fetching Stripe config...")
        config_resp = await client.get("http://localhost:8000/api/stripe/config")
        config = config_resp.json()
        
        # Use Pro Monthly price if available, otherwise fake one
        prices = config.get("data", {}).get("prices", {})
        price_id = prices.get("pro_monthly", "price_fake_pro_monthly")
        print(f"Using Price ID: {price_id}")

        # 3. Simulate Webhook
        payload_dict = {
            "id": f"evt_test_{int(time.time())}",
            "object": "event",
            "type": "checkout.session.completed",
            "created": int(time.time()),
            "data": {
                "object": {
                    "id": f"cs_test_simulated_{int(time.time())}",
                    "object": "checkout.session",
                    "amount_total": 499,
                    "currency": "usd",
                    "payment_status": "paid",
                    "status": "complete",
                    "client_reference_id": USER_ID,
                    "metadata": {
                        "userId": USER_ID,
                        "userEmail": "demo@mentobai.com",
                        "priceId": price_id
                    }
                }
            }
        }
        
        payload_str = json.dumps(payload_dict)
        
        # Generate Signature
        timestamp = int(time.time())
        signed_payload = f"{timestamp}.{payload_str}"
        
        signature = hmac.new(
            key=STRIPE_WEBHOOK_SECRET.encode('utf-8'),
            msg=signed_payload.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        header = f"t={timestamp},v1={signature}"
        
        print(f"Sending webhook payload to {API_URL}...")
        resp = await client.post(
            API_URL, 
            content=payload_str,
            headers={
                "stripe-signature": header,
                "Content-Type": "application/json"
            }
        )
        
        print(f"Webhook Response Code: {resp.status_code}")
        print(f"Webhook Response Body: {resp.text}")
        
        if resp.status_code == 200 and resp.json().get("success"):
            print("✅ Webhook processed successfully!")
            print("Check your database 'payments' table and 'users' vip_level.")
        else:
            print("❌ Webhook failed.")

if __name__ == "__main__":
    asyncio.run(main())
