from app.database import supabase
from app.models import QuotaResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QuotaService:
    DAILY_LIMIT = 3

    @staticmethod
    async def get_user_quota(user_id: str, is_demo: bool = False) -> QuotaResponse:
        """
        Get user's current quota status.
        Resets to 3 if it's a new day (implied by no record for today).
        """
        if is_demo:
            return QuotaResponse(
                remaining=999999,
                used=0,
                total="Unlimited",
                isDemo=True
            )

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Check daily_quotas table
            response = supabase.table("daily_quotas").select("*").eq("user_id", user_id).eq("date", today).execute()
            
            used = 0
            if response.data:
                used = response.data[0]["count"]
            
            # Logic: New day (no record) -> used=0 -> remaining=3
            remaining = max(0, QuotaService.DAILY_LIMIT - used)
            
            return QuotaResponse(
                remaining=remaining,
                used=used,
                total=QuotaService.DAILY_LIMIT,
                isDemo=False
            )
        except Exception as e:
            logger.error(f"Error getting quota for user {user_id}: {e}")
            # Fallback to 0 remaining to be safe, or 3 if we assume error shouldn't block?
            # Safe approach: return 0 or raise
            raise e

    @staticmethod
    async def reduce_quota(user_id: str) -> bool:
        """
        Reduce user's quota by 1.
        Returns True if successful, False if quota exceeded.
        Handles the 'reset to 3' logic implicitly by creating a new daily record if none exists.
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Check current usage
            response = supabase.table("daily_quotas").select("*").eq("user_id", user_id).eq("date", today).execute()
            
            current_count = 0
            record_id = None
            
            if response.data:
                current_count = response.data[0]["count"]
                record_id = response.data[0]["id"]
            
            if current_count >= QuotaService.DAILY_LIMIT:
                logger.warning(f"User {user_id} quota exceeded")
                return False
            
            # Update or Insert
            if record_id:
                supabase.table("daily_quotas").update({"count": current_count + 1}).eq("id", record_id).execute()
            else:
                # New day or new user -> Start with 1 used (effectively reset to 3 then used 1)
                supabase.table("daily_quotas").insert({"user_id": user_id, "date": today, "count": 1}).execute()
                
            return True
            
        except Exception as e:
            logger.error(f"Error reducing quota for user {user_id}: {e}")
            raise e

    @staticmethod
    async def initialize_quota(user_id: str):
        """
        Explicitly initialize quota for a new user (Optional).
        Sets count to 0 for today.
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            # Check if exists (should not for new user, but safety first)
            response = supabase.table("daily_quotas").select("*").eq("user_id", user_id).eq("date", today).execute()
            if not response.data:
                 supabase.table("daily_quotas").insert({"user_id": user_id, "date": today, "count": 0}).execute()
        except Exception as e:
            logger.error(f"Error initializing quota for user {user_id}: {e}")
            # Non-critical, swallow error
            pass
