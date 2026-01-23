import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.quota import QuotaService
from app.database import SessionLocal
from app.db_models import User
from sqlalchemy.orm import Session

def main():
    # Demo User ID (from auth.py)
    user_id = "00000000-0000-0000-0000-000000000000"
    print(f"Testing VIP Quota Logic for User: {user_id}")
    
    db = SessionLocal()

    try:
        # 1. Get current state from DB directly
        print("Fetching initial state...")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print("Error: User not found.")
            return
        
        initial_quota = user.quota
        vip_level = user.vip_level
        vip_expire_at = user.vip_expire_at
        
        print(f"Initial State -> Quota: {initial_quota}, VIP Level: {vip_level}, Expire: {vip_expire_at}")
        
        if vip_level == 0:
            print("Warning: User is not VIP. Test might not verify VIP protection.")
        
        # 2. Attempt to reduce quota
        print("Calling QuotaService.reduce_quota()...")
        
        try:
            # Pass the session explicitly
            result = QuotaService.reduce_quota(user_id, db)
            print(f"reduce_quota returned: {result}")
        except Exception as e:
            print(f"Error calling reduce_quota: {e}")
            import traceback
            traceback.print_exc()
            return

        # 3. Verify Quota
        print("Fetching final state...")
        # Refresh user or query again
        db.refresh(user)
        final_quota = user.quota
        
        print(f"Final Quota: {final_quota}")
        
        if initial_quota == final_quota:
            print("✅ SUCCESS: Quota was NOT reduced.")
        else:
            print(f"❌ FAILURE: Quota changed from {initial_quota} to {final_quota}")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
