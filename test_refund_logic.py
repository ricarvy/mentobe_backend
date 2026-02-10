import asyncio
import logging
from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.db_models import User, Payment
from app.routers.stripe import handle_charge_refunded
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from unittest.mock import patch

async def test_refund_logic():
    print("--- Starting Refund Logic Test ---")
    db = SessionLocal()
    
    try:
        # 1. Setup Test User
        test_email = "refund_test@example.com"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            user = User(
                email=test_email,
                username="RefundTester",
                password="hash", # Changed from hashed_password
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created test user: {user.id}")
        
        # 2. Simulate Purchase (Set VIP)
        now = datetime.now(timezone.utc)
        expire_date = now + timedelta(days=30)
        
        user.vip_level = 1
        user.vip_expire_at = expire_date
        db.commit()
        print(f"User set to VIP Level 1, Expires: {expire_date}")
        
        # 3. Create Test Payment
        # Use a dummy price ID, we will patch get_vip_info
        price_id = "price_test_pro_monthly"
            
        payment = Payment(
            user_id=str(user.id),
            stripe_session_id="sess_test_refund",
            amount_total=990,
            currency="usd",
            status="paid",
            price_id=price_id,
            vip_level=1,
            vip_duration="monthly"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        print(f"Created test payment: {payment.id}")
        
        # 4. Simulate Charge Refunded Event Payload
        charge_payload = {
            "id": "ch_test_refund",
            "payment_intent": "pi_test_refund",
            "metadata": {
                "userId": str(user.id),
                "priceId": price_id
            }
        }
        
        print("Simulating handle_charge_refunded...")
        
        # Patch get_vip_info to ensure it returns Level 1, 30 days
        with patch('app.routers.stripe.get_vip_info', return_value=(1, 30)):
            await handle_charge_refunded(charge_payload)
        
        # 5. Verify Results
        # Commit current transaction to ensure we see updates from other sessions
        db.commit() 
        db.refresh(user)
        db.refresh(payment)
        
        print("\n--- Verification ---")
        
        # Check Payment Status
        if payment.status == "refunded":
            print("✅ Payment status updated to 'refunded'")
        else:
            print(f"❌ Payment status failed: {payment.status}")
            
        # Check User Benefit
        print(f"User VIP Level: {user.vip_level}")
        print(f"User Expire At: {user.vip_expire_at}")
        
        # Fix datetime comparison
        user_expire = user.vip_expire_at
        if user_expire and user_expire.tzinfo is None:
            user_expire = user_expire.replace(tzinfo=timezone.utc)
            
        if user.vip_level == 0:
            print("✅ User downgraded to Free (Level 0)")
        else:
            # Check if expiry was reduced
            # We started with +30 days. We subtracted 30 days. Should be near 'now'.
            # Allow some margin
            if user_expire < now + timedelta(minutes=5):
                 print(f"✅ User expiry reduced correctly (Is near now: {user_expire})")
            else:
                 print(f"❌ User expiry check failed. Expected near {now}, got {user_expire}")

    except Exception as e:
        print(f"Test Error: {e}")
    finally:
        # Cleanup
        if 'user' in locals() and user:
            db.query(Payment).filter(Payment.user_id == user.id).delete()
            db.delete(user)
            db.commit()
            print("Cleanup completed.")
        db.close()

if __name__ == "__main__":
    asyncio.run(test_refund_logic())
