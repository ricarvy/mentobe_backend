import httpx
import asyncio
import json
import time

# Configuration
API_URL = "http://localhost:8000/api/stripe/webhook"
# Demo user UUID as defined in auth.py
USER_ID = "00000000-0000-0000-0000-000000000000"
# Example Price ID (Pro Monthly) - Ensure this matches your .env or just use a placeholder if your logic handles it
# Logic in stripe.py checks against settings. So we should use a value that might match if we want VIP update.
# But since we don't have easy access to settings values here without importing, let's assume one or fetch it.
# Actually, we can fetch the config first!

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Login to ensure Demo User exists in DB
        print("Logging in to ensure Demo User exists...")
        login_resp = await client.post("http://localhost:8000/api/auth/login", json={
            "email": "demo@mentobai.com",
            "password": "Demo123!"
        })
        print(f"Login status: {login_resp.status_code}")
        if login_resp.status_code != 200:
            print("Login failed, aborting.")
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
        payload = {
            "type": "checkout.session.completed",
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
        
        print(f"Sending webhook payload to {API_URL}...")
        resp = await client.post(API_URL, json=payload)
        
        print(f"Webhook Response Code: {resp.status_code}")
        print(f"Webhook Response Body: {resp.text}")
        
        if resp.status_code == 200 and resp.json().get("success"):
            print("✅ Webhook processed successfully!")
            print("Check your database 'payments' table and 'users' vip_level.")
        else:
            print("❌ Webhook failed.")

if __name__ == "__main__":
    asyncio.run(main())
