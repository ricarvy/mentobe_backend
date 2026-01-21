import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.quota import QuotaService
from app.database import get_db, SessionLocal
# from app.models import User
from sqlalchemy.orm import Session
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Setup Supabase client for verification
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

async def main():
    # Demo User ID (from auth.py)
    user_id = "00000000-0000-0000-0000-000000000000"
    print(f"Testing VIP Quota Logic for User: {user_id}")

    # 1. Get current state from DB directly via Supabase (source of truth)
    print("Fetching initial state...")
    res = supabase.table("users").select("quota, vip_level, vip_expire_at").eq("id", user_id).execute()
    if not res.data:
        print("Error: User not found.")
        return
    
    user_data = res.data[0]
    initial_quota = user_data['quota']
    vip_level = user_data['vip_level']
    vip_expire_at = user_data['vip_expire_at']
    
    print(f"Initial State -> Quota: {initial_quota}, VIP Level: {vip_level}, Expire: {vip_expire_at}")
    
    if vip_level == 0:
        print("Warning: User is not VIP. Test might not verify VIP protection.")
        # We might want to temporarily upgrade user for test? 
        # But previous turns confirmed VIP level 1.
    
    # 2. Attempt to reduce quota
    print("Calling QuotaService.reduce_quota()...")
    # We need to run this in a way that uses the DB session if needed.
    # QuotaService.reduce_quota manages its own session via Depends? 
    # No, it's a static method that calls `get_user_quota` etc.
    # Let's check QuotaService implementation again.
    # It likely uses `get_db` or creates session inside?
    # Actually, in `app/services/quota.py`, the methods are static and often expect a DB session OR use a context manager?
    # I'll check `quota.py` content to be sure how to call it.
    
    # Assuming it works with standard DB access.
    try:
        result = await QuotaService.reduce_quota(user_id)
        print(f"reduce_quota returned: {result}")
    except Exception as e:
        print(f"Error calling reduce_quota: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Verify Quota
    print("Fetching final state...")
    res_final = supabase.table("users").select("quota").eq("id", user_id).execute()
    final_quota = res_final.data[0]['quota']
    
    print(f"Final Quota: {final_quota}")
    
    if initial_quota == final_quota:
        print("✅ SUCCESS: Quota was NOT reduced.")
    else:
        print(f"❌ FAILURE: Quota changed from {initial_quota} to {final_quota}")

if __name__ == "__main__":
    asyncio.run(main())
