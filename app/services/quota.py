from app.database import supabase
from app.models import QuotaResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QuotaService:
    DAILY_LIMIT = 3

    @staticmethod
    async def _check_and_reset_daily_quota(user_id: str):
        """
        Check if quota needs to be reset for the new day.
        If no record exists in daily_quotas for today, reset users.quota to 3 and insert daily record.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check daily_quotas table for today's record (as a flag)
        response = supabase.table("daily_quotas").select("id").eq("user_id", user_id).eq("date", today).execute()
        
        if not response.data:
            logger.info(f"New day detected for user {user_id}. Resetting quota to {QuotaService.DAILY_LIMIT}.")
            # 1. Reset users.quota to 3
            supabase.table("users").update({"quota": QuotaService.DAILY_LIMIT}).eq("id", user_id).execute()
            # 2. Insert record into daily_quotas to mark today as initialized
            # We don't strictly need 'count' anymore if we trust users.quota, but let's keep it for logging/flagging
            # Or we can just use it as a flag. count=0 is fine.
            supabase.table("daily_quotas").insert({"user_id": user_id, "date": today, "count": 0}).execute()

    @staticmethod
    async def get_user_quota(user_id: str, is_demo: bool = False) -> QuotaResponse:
        """
        Get user's current quota status from users table.
        Auto-resets if it's a new day.
        """
        if is_demo:
            return QuotaResponse(
                remaining=999999,
                used=0,
                total="Unlimited",
                isDemo=True
            )

        try:
            # Check and reset if needed
            await QuotaService._check_and_reset_daily_quota(user_id)
            
            # Get quota from users table
            u_res = supabase.table("users").select("quota").eq("id", user_id).execute()
            
            remaining = 0
            if u_res.data:
                # Default to 0 if null, though should be 3 if reset
                remaining = u_res.data[0].get("quota", 0)
                if remaining is None: remaining = 0 # Safety
            
            # Calculated used (approximation, since we don't strictly track 'used' in this new logic, only remaining)
            # But for display: Total - Remaining = Used
            used = max(0, QuotaService.DAILY_LIMIT - remaining)
            
            return QuotaResponse(
                remaining=remaining,
                used=used,
                total=QuotaService.DAILY_LIMIT,
                isDemo=False
            )
        except Exception as e:
            logger.error(f"Error getting quota for user {user_id}: {e}")
            raise e

    @staticmethod
    async def reduce_quota(user_id: str) -> bool:
        """
        Reduce user's quota by 1 in users table.
        Returns True if successful, False if quota exceeded.
        """
        try:
            # Check and reset if needed
            await QuotaService._check_and_reset_daily_quota(user_id)
            
            # Check current quota
            u_res = supabase.table("users").select("quota").eq("id", user_id).execute()
            
            current_quota = 0
            if u_res.data:
                current_quota = u_res.data[0].get("quota", 0)
                if current_quota is None: current_quota = 0
            
            if current_quota <= 0:
                logger.warning(f"User {user_id} quota exhausted")
                return False
            
            # Reduce by 1
            new_quota = current_quota - 1
            supabase.table("users").update({"quota": new_quota}).eq("id", user_id).execute()
            
            # Optionally update daily_quotas count for history/stats if desired
            # But user requirement focuses on users.quota. Let's keep daily_quotas as just a date flag or stats.
            # Let's increment daily_quotas count too for good measure (stats)
            today = datetime.now().strftime("%Y-%m-%d")
            # We know it exists because of _check_and_reset_daily_quota
            # But to be safe (race condition?), just try update
            # Getting the id first is safer or just use match
            dq_res = supabase.table("daily_quotas").select("id, count").eq("user_id", user_id).eq("date", today).execute()
            if dq_res.data:
                d_id = dq_res.data[0]["id"]
                d_count = dq_res.data[0]["count"]
                supabase.table("daily_quotas").update({"count": d_count + 1}).eq("id", d_id).execute()
                
            return True
            
        except Exception as e:
            logger.error(f"Error reducing quota for user {user_id}: {e}")
            raise e

    @staticmethod
    async def initialize_quota(user_id: str):
        """
        Explicitly initialize quota for a new user.
        Sets users.quota = 3 and creates daily record.
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 1. Set users.quota = 3
            # (If not already set by default value in DB)
            supabase.table("users").update({"quota": QuotaService.DAILY_LIMIT}).eq("id", user_id).execute()
            
            # 2. Create daily record
            response = supabase.table("daily_quotas").select("*").eq("user_id", user_id).eq("date", today).execute()
            if not response.data:
                 supabase.table("daily_quotas").insert({"user_id": user_id, "date": today, "count": 0}).execute()
                 
        except Exception as e:
            logger.error(f"Error initializing quota for user {user_id}: {e}")
            pass
