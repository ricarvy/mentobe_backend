import time
import json
import uuid
import hmac
import hashlib
import requests
import logging
import argparse

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configs
LOCAL_CONFIG = {
    "name": "Local Environment",
    "api_base": "http://localhost:8901",
    "webhook_url": "http://localhost:8901/api/stripe/webhook",
    "secret": "whsec_NUd81BfIEM2COWvsOYcksNRnuqKpRhug", 
    "price_id": "price_1Sren7GVP93aj81Tr4d18z2S"
}

ONLINE_PROD_CONFIG = {
    "name": "Online Production Environment",
    "api_base": "https://api.mentobe.co",
    "webhook_url": "https://api.mentobe.co/api/stripe/webhook",
    "secret": "whsec_zYMs6WfJtOy4SoJmfe1Hc8PnRyv7V12H",
    "price_id": "price_1Sv8CpJLkngja4kbsTzSSAfi"
}

def generate_email(env_name):
    timestamp = int(time.time())
    # Clean env name for email
    clean_name = env_name.split()[0].lower()
    return f"test_{clean_name}_{timestamp}@example.com"

def register_and_login(config):
    api_base = config["api_base"]
    email = generate_email(config["name"])
    password = "TestPassword123!"
    
    # 1. Register
    logger.info(f"[{config['name']}] 1. Registering new user: {email}")
    try:
        reg_res = requests.post(f"{api_base}/api/auth/register", json={
            "email": email,
            "password": password
        })
        if reg_res.status_code != 200:
            logger.error(f"[{config['name']}] Registration failed: {reg_res.text}")
            return None, None, None, None
        
        user_data = reg_res.json()
        user_id = None
        if "data" in user_data:
            user_id = user_data["data"].get("id")
        else:
            user_id = user_data.get("id")
            
        logger.info(f"[{config['name']}] Registration successful.")
    except Exception as e:
        logger.error(f"[{config['name']}] Registration error: {e}")
        return None, None, None, None

    # 2. Login
    logger.info(f"[{config['name']}] 2. Logging in to get Token...")
    try:
        login_res = requests.post(f"{api_base}/api/auth/login", json={
            "email": email,
            "password": password
        })
        
        if login_res.status_code != 200:
            logger.error(f"[{config['name']}] Login failed: {login_res.text}")
            return None, None, None, None
        
        login_data = login_res.json()
        token = login_data.get("data", {}).get("accessToken")
        
        if not user_id and token:
             user_id = login_data.get("data", {}).get("id")

        if token and user_id:
            logger.info(f"[{config['name']}] Login successful. User ID: {user_id}")
            return user_id, token, email, password
        else:
            logger.error(f"[{config['name']}] Could not get token or user_id.")
            return None, None, None, None
            
    except Exception as e:
        logger.error(f"[{config['name']}] Login error: {e}")
        return None, None, None, None

def send_webhook(config, user_id):
    url = config["webhook_url"]
    secret = config["secret"]
    price_id = config["price_id"]
    
    logger.info(f"[{config['name']}] 3. Sending Webhook to: {url}")
    
    timestamp = int(time.time())
    session_id = f"cs_test_{timestamp}"
    
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
                    "priceId": price_id
                },
                "subscription": None 
            }
        }
    }
    
    payload_str = json.dumps(event_payload)
    
    signed_payload = f"{timestamp}.{payload_str}"
    signature = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": f"t={timestamp},v1={signature}"
    }
    
    try:
        response = requests.post(url, data=payload_str, headers=headers)
        logger.info(f"[{config['name']}] Webhook Response: {response.status_code}")
        logger.info(f"[{config['name']}] Response Body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[{config['name']}] Webhook Request Error: {e}")
        return False

def verify_vip(config, email, password):
    logger.info(f"[{config['name']}] 4. Verifying VIP status...")
    time.sleep(3) # Wait for DB update
    
    try:
        res = requests.post(f"{config['api_base']}/api/auth/login", json={
            "email": email,
            "password": password
        })
        
        if res.status_code == 200:
            data = res.json().get("data", {})
            vip_level = data.get("vipLevel")
            expire_at = data.get("vipExpireAt")
            logger.info(f"[{config['name']}] User Info: VIP Level={vip_level}, Expire={expire_at}")
            
            if vip_level == 1:
                logger.info(f"[{config['name']}] ✅ SUCCESS: VIP Level updated to 1")
                return True
            else:
                logger.error(f"[{config['name']}] ❌ FAILURE: VIP Level is {vip_level} (Expected 1)")
                return False
        else:
            logger.error(f"[{config['name']}] Failed to login for verification: {res.status_code}")
            return False
    except Exception as e:
        logger.error(f"[{config['name']}] Verification error: {e}")
        return False

def run_test(config):
    logger.info(f"\n=== TESTING {config['name']} ===")
    user_id, token, email, password = register_and_login(config)
    if not user_id:
        return
    
    if send_webhook(config, user_id):
        verify_vip(config, email, password)
    else:
        logger.error(f"[{config['name']}] Webhook failed, skipping verification.")

if __name__ == "__main__":
    run_test(LOCAL_CONFIG)
    run_test(ONLINE_PROD_CONFIG)
