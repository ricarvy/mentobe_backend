from app.database import supabase
from app.models import QuotaResponse
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class QuotaService:
    DAILY_LIMIT = 3

    @staticmethod
    async def _check_and_reset_daily_quota(user_id: str):
        """
        Check if quota needs to be reset for the new day.
        If no record exists in daily_quotas for today, check VIP status:
        - If VIP and not expired: Do not reset quota (keep it high/unlimited).
        - If not VIP: Reset users.quota to 3.
        Always insert daily record to mark the day as checked.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check daily_quotas table for today's record (as a flag)
        response = supabase.table("daily_quotas").select("id").eq("user_id", user_id).eq("date", today).execute()
        
        if not response.data:
            logger.info(f"New day detected for user {user_id}.")
            
            # Check VIP status
            user_res = supabase.table("users").select("vip_level, vip_expire_at").eq("id", user_id).execute()
            is_valid_vip = False
            if user_res.data:
                user_data = user_res.data[0]
                vip_level = user_data.get("vip_level", 0)
                vip_expire_at_str = user_data.get("vip_expire_at")
                
                if vip_level > 0 and vip_expire_at_str:
                    try:
                        vip_expire_at_str = vip_expire_at_str.replace('Z', '+00:00')
                        expire_at = datetime.fromisoformat(vip_expire_at_str)
                        if expire_at > datetime.now(timezone.utc):
                            is_valid_vip = True
                    except ValueError:
                        pass

            if is_valid_vip:
                logger.info(f"User {user_id} is VIP. Skipping quota reset.")
                # Optional: Ensure it's high if for some reason it dropped? 
                # For now, we assume payment set it to 999999. We just don't reset it to 3.
            else:
                logger.info(f"User {user_id} is not VIP. Resetting quota to {QuotaService.DAILY_LIMIT}.")
                supabase.table("users").update({"quota": QuotaService.DAILY_LIMIT}).eq("id", user_id).execute()

            # Insert record into daily_quotas to mark today as initialized
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
            
            # Get quota and VIP info from users table
            u_res = supabase.table("users").select("quota, vip_level, vip_expire_at").eq("id", user_id).execute()
            
            remaining = 0
            is_valid_vip = False
            
            if u_res.data:
                user_data = u_res.data[0]
                remaining = user_data.get("quota", 0)
                if remaining is None: remaining = 0
                
                vip_level = user_data.get("vip_level", 0)
                vip_expire_at_str = user_data.get("vip_expire_at")
                
                if vip_level > 0 and vip_expire_at_str:
                    try:
                        vip_expire_at_str = vip_expire_at_str.replace('Z', '+00:00')
                        expire_at = datetime.fromisoformat(vip_expire_at_str)
                        if expire_at > datetime.now(timezone.utc):
                            is_valid_vip = True
                    except ValueError:
                        pass
            
            total_display = "Unlimited" if is_valid_vip else QuotaService.DAILY_LIMIT
            used = 0 if is_valid_vip else max(0, QuotaService.DAILY_LIMIT - remaining)
            
            return QuotaResponse(
                remaining=remaining,
                used=used,
                total=total_display,
                isDemo=False
            )
        except Exception as e:
            logger.error(f"Error getting quota for user {user_id}: {e}")
            raise e

    @staticmethod
    async def reduce_quota(user_id: str) -> bool:
        """
        Reduce user's quota by 1 in users table.
        If VIP and not expired, do NOT reduce quota (return True).
        Returns True if successful, False if quota exceeded.
        """
        try:
            # Check and reset if needed
            await QuotaService._check_and_reset_daily_quota(user_id)
            
            # Check current quota and VIP status
            u_res = supabase.table("users").select("quota, vip_level, vip_expire_at").eq("id", user_id).execute()
            
            current_quota = 0
            is_valid_vip = False
            
            if u_res.data:
                user_data = u_res.data[0]
                current_quota = user_data.get("quota", 0)
                if current_quota is None: current_quota = 0
                
                vip_level = user_data.get("vip_level", 0)
                vip_expire_at_str = user_data.get("vip_expire_at")
                
                if vip_level > 0 and vip_expire_at_str:
                    try:
                        vip_expire_at_str = vip_expire_at_str.replace('Z', '+00:00')
                        expire_at = datetime.fromisoformat(vip_expire_at_str)
                        if expire_at > datetime.now(timezone.utc):
                            is_valid_vip = True
                    except ValueError:
                        pass
            
            # If VIP, don't reduce quota, just return True
            if is_valid_vip:
                logger.info(f"User {user_id} is VIP. Skipping quota reduction.")
                return True

            if current_quota <= 0:
                logger.warning(f"User {user_id} quota exhausted")
                return False
            
            # Reduce by 1
            new_quota = current_quota - 1
            supabase.table("users").update({"quota": new_quota}).eq("id", user_id).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error reducing quota for user {user_id}: {e}")
            return False
