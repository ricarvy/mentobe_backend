import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.db_models import User
from datetime import datetime, timedelta, timezone

def fix_user_expiry():
    db = SessionLocal()
    try:
        # User d3384bb4...
        # Originally had expiration around 2026-08-02.
        # We mistakenly reset it to 2026-03-07.
        # The user wants to "add to original expiration".
        # So we should restore to 2026-08-02 + 30 days.
        
        user_id_prefix = "d3384bb4"
        print(f"--- Fixing User {user_id_prefix}... ---")
        
        user = db.query(User).filter(User.id.like(f"{user_id_prefix}%")).first()
        
        if not user:
            print("User not found.")
            return

        print(f"User: {user.id}")
        print(f"Current VIP Level: {user.vip_level}")
        print(f"Current Expire At: {user.vip_expire_at}")
        
        # Original expiration (reconstructed from log: 2026-08-02)
        # We will assume 2026-08-02 05:19:38 (from previous log)
        # Note: Previous log said "Current Expire At: 2026-08-02 05:19:38"
        
        original_expire_str = "2026-08-02 05:19:38"
        original_expire_dt = datetime.strptime(original_expire_str, "%Y-%m-%d %H:%M:%S")
        original_expire_dt = original_expire_dt.replace(tzinfo=timezone.utc)
        
        # Add 30 days (Monthly Upgrade)
        new_expire_dt = original_expire_dt + timedelta(days=30)
        
        print(f"Restoring logic: {original_expire_dt} + 30 days = {new_expire_dt}")
        
        user.vip_expire_at = new_expire_dt
        user.vip_level = 2 # Ensure Premium
        db.add(user)
        db.commit()
        
        print(f"User updated successfully.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_user_expiry()
