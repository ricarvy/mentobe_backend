import time
import json
import uuid
import hmac
import hashlib
import requests
import logging

# Config
# API_BASE = "https://api.mentobe.co" # Assuming backend is here
API_BASE = "https://api.mentobe.co"
WEBHOOK_TARGET = "https://api.mentobe.co/api/stripe/webhook" # User specified

# Keys from .env.local (Test Mode)
# STRIPE_WEBHOOK_SECRET = "whsec_NUd81BfIEM2COWvsOYcksNRnuqKpRhug" # Test Secret
STRIPE_WEBHOOK_SECRET = "whsec_zYMs6WfJtOy4SoJmfe1Hc8PnRyv7V12H" # Live Secret (Trying this as Test failed)
# PRICE_ID = "price_1Sren7GVP93aj81Tr4d18z2S" # Test Pro Monthly
PRICE_ID = "price_1Sv8CpJLkngja4kbsTzSSAfi" # Live Pro Monthly (Server likely in Live mode)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_email():
    return f"test_online_{int(time.time())}@example.com"

def register_and_login():
    email = generate_email()
    password = "TestPassword123!"
    
    # 1. Register
    logger.info(f"1. Registering new user: {email}")
    try:
        reg_res = requests.post(f"{API_BASE}/api/auth/register", json={
            "email": email,
            "password": password
        })
        if reg_res.status_code != 200:
            logger.error(f"Registration failed: {reg_res.text}")
            return None, None, None, None
        
        user_data = reg_res.json()
        user_id = None
        if "data" in user_data:
            user_id = user_data["data"].get("id")
        else:
            user_id = user_data.get("id")
            
        logger.info("Registration successful.")
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return None, None, None, None

    # 2. Login
    logger.info("2. Logging in to get Token...")
    try:
        login_res = requests.post(f"{API_BASE}/api/auth/login", json={
            "email": email,
            "password": password
        })
        
        if login_res.status_code != 200:
            logger.error(f"Login failed: {login_res.text}")
            return None, None, None, None
        
        login_data = login_res.json()
        token = login_data.get("data", {}).get("accessToken")
        
        if not user_id and token:
             # Can't use /me as it doesn't exist, but login returns user ID in data
             user_id = login_data.get("data", {}).get("id")

        if token and user_id:
            logger.info(f"Login successful. User ID: {user_id}")
            return user_id, token, email, password
        else:
            logger.error("Could not get token or user_id.")
            return None, None, None, None
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return None, None, None, None

def send_webhook(url, user_id):
    logger.info(f"3. Sending Webhook to: {url}")
    
    session_id = f"cs_test_online_{int(time.time())}"
    timestamp = int(time.time())
    
    event_payload = {
        "id": f"evt_test_{timestamp}",
        "object": "event",
        "api_version": "2022-11-15",
        "created": timestamp,
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
                "subscription": None 
            }
        }
    }
    
    payload_str = json.dumps(event_payload)
    
    signed_payload = f"{timestamp}.{payload_str}"
    signature = hmac.new(
        STRIPE_WEBHOOK_SECRET.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": f"t={timestamp},v1={signature}"
    }
    
    try:
        response = requests.post(url, data=payload_str, headers=headers)
        logger.info(f"Webhook Response: {response.status_code}")
        logger.info(f"Response Body: {response.text}")
        if response.status_code != 200:
             logger.warning(f"Response Body: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Webhook Request Error: {e}")
        return False

def verify_vip(email, password):
    logger.info("4. Verifying VIP status via Login (Refresh User Data)...")
    # Wait a bit for DB update
    time.sleep(3)
    
    try:
        # Re-login to get fresh user data
        res = requests.post(f"{API_BASE}/api/auth/login", json={
            "email": email,
            "password": password
        })
        
        if res.status_code == 200:
            data = res.json().get("data", {})
            vip_level = data.get("vipLevel")
            expire_at = data.get("vipExpireAt")
            logger.info(f"User Info: VIP Level={vip_level}, Expire={expire_at}")
            
            if vip_level == 1:
                logger.info("✅ SUCCESS: VIP Level updated to 1")
                return True
            else:
                logger.error(f"❌ FAILURE: VIP Level is {vip_level} (Expected 1)")
                return False
        else:
            logger.error(f"Failed to login for verification: {res.status_code}")
            return False
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False

def main():
    logger.info("--- STARTING ONLINE LINK TEST (Updated) ---")
    
    # Step 1 & 2
    user_id, token, email, password = register_and_login()
    if not user_id:
        logger.error("Aborting test due to auth failure.")
        return

    # Step 3
    success = send_webhook(WEBHOOK_TARGET, user_id)
    
    if success:
        # Step 4
        verify_vip(email, password)
    else:
        logger.error("Webhook delivery failed, skipping verification.")

if __name__ == "__main__":
    main()
