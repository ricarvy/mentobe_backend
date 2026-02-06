import asyncio
import logging
from app.routers.stripe import _handle_checkout_completed_sync
from app.config import settings

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def run_test():
    user_id = "3df15404-af59-4f0c-9b91-a5527daf3cb0" # ricarvyli@gmail.com
    
    # 1. Test with configured Price ID (from .env.local) - SHOULD SUCCEED
    print("\n--- Test 1: Using configured Price ID ---")
    price_id = settings.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY
    # Hardcode the TEST price ID to be sure we are testing what we think we are testing
    # price_id = "price_1Sren7GVP93aj81Tr4d18z2S" 
    print(f"Configured Price ID: {price_id}")
    
    session = {
        "id": "cs_test_simulated_3",
        "client_reference_id": user_id,
        "amount_total": 1000,
        "currency": "usd",
        "payment_status": "paid",
        "metadata": {
            "userId": user_id,
            "priceId": price_id
        }
    }
    
    try:
        _handle_checkout_completed_sync(session)
        print("Test 1 Completed")
    except Exception as e:
        print(f"Test 1 Failed: {e}")

    # 2. Test with Live Price ID (should fail in Test environment)
    print("\n--- Test 2: Using Live Price ID (Should Fail) ---")
    live_price_id = "price_1Sv8CpJLkngja4kbsTzSSAfi"
    print(f"Live Price ID: {live_price_id}")
    
    session_live = {
        "id": "cs_live_simulated_4",
        "client_reference_id": user_id,
        "amount_total": 1000,
        "currency": "usd",
        "payment_status": "paid",
        "metadata": {
            "userId": user_id,
            "priceId": live_price_id
        }
    }
    
    try:
        _handle_checkout_completed_sync(session_live)
        print("Test 2 Completed")
    except Exception as e:
        print(f"Test 2 Failed: {e}")

if __name__ == "__main__":
    run_test()
