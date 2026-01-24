from sqlalchemy.orm import Session
from app.db_models import User, DailyQuota
from app.models import QuotaResponse
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class QuotaService:
    DAILY_LIMIT = 3

    @staticmethod
    def _check_and_reset_daily_quota(user_id: str, db: Session):
        """
        Check if quota needs to be reset for the new day.
        If no record exists in daily_quotas for today, check VIP status:
        - If VIP and not expired: Do not reset quota (keep it high/unlimited).
        - If not VIP: Reset users.quota to 3.
        Always insert daily record to mark the day as checked.
        """
        today = datetime.now().date()
        
        # Check daily_quotas table for today's record (as a flag)
        record = db.query(DailyQuota).filter(DailyQuota.user_id == user_id, DailyQuota.date == today).first()
        
        if not record:
            logger.info(f"New day detected for user {user_id}.")
            
            # Check VIP status
            user = db.query(User).filter(User.id == user_id).first()
            is_valid_vip = False
            if user:
                vip_level = user.vip_level or 0
                vip_expire_at = user.vip_expire_at
                
                if vip_level > 0 and vip_expire_at:
                    # Ensure timezone awareness
                    if vip_expire_at.tzinfo is None:
                        vip_expire_at = vip_expire_at.replace(tzinfo=timezone.utc)
                    if vip_expire_at > datetime.now(timezone.utc):
                        is_valid_vip = True

            if is_valid_vip:
                logger.info(f"User {user_id} is VIP. Skipping quota reset.")
            else:
                logger.info(f"User {user_id} is not VIP. Resetting quota to {QuotaService.DAILY_LIMIT}.")
                if user:
                    user.quota = QuotaService.DAILY_LIMIT
                    db.add(user)

            # Insert record into daily_quotas to mark today as initialized
            new_daily = DailyQuota(user_id=user_id, date=today, count=0)
            db.add(new_daily)
            db.commit()

    @staticmethod
    def get_user_quota(user_id: str, db: Session, is_demo: bool = False) -> QuotaResponse:
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
            QuotaService._check_and_reset_daily_quota(user_id, db)
            
            # Get quota and VIP info from users table
            user = db.query(User).filter(User.id == user_id).first()
            
            remaining = 0
            is_valid_vip = False
            
            if user:
                remaining = user.quota or 0
                
                vip_level = user.vip_level or 0
                vip_expire_at = user.vip_expire_at
                
                if vip_level > 0 and vip_expire_at:
                    if vip_expire_at.tzinfo is None:
                        vip_expire_at = vip_expire_at.replace(tzinfo=timezone.utc)
                    if vip_expire_at > datetime.now(timezone.utc):
                        is_valid_vip = True
            
            total_display = "Unlimited" if is_valid_vip else QuotaService.DAILY_LIMIT
            used = 0 if is_valid_vip else max(0, QuotaService.DAILY_LIMIT - remaining)
            
            return QuotaResponse(
                remaining=remaining,
                used=used,
                total=total_display,
                isDemo=False
            )
        except Exception as e:
            logger.error(f"Error getting user quota: {e}")
            return QuotaResponse(
                remaining=0,
                used=0,
                total=QuotaService.DAILY_LIMIT,
                isDemo=False
            )

    @staticmethod
    def reduce_quota(user_id: str, db: Session) -> bool:
        """
        Reduce user's quota by 1.
        Updates 'users' table and increments 'daily_quotas'.
        If user is VIP, do not reduce quota.
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Check VIP status
            is_valid_vip = False
            vip_level = user.vip_level or 0
            vip_expire_at = user.vip_expire_at
            
            if vip_level > 0 and vip_expire_at:
                if vip_expire_at.tzinfo is None:
                    vip_expire_at = vip_expire_at.replace(tzinfo=timezone.utc)
                if vip_expire_at > datetime.now(timezone.utc):
                    is_valid_vip = True
            
            if is_valid_vip:
                logger.info(f"User {user_id} is VIP. Skipping quota reduction.")
                # Even if VIP, we need to commit the transaction because we might have added an interpretation record in the session
                db.commit()
                return True

            current_quota = user.quota or 0
            if current_quota <= 0:
                return False
            
            # Reduce quota
            new_quota = current_quota - 1
            user.quota = new_quota
            db.add(user)
            
            # Update daily usage count
            today = datetime.now().date()
            daily_record = db.query(DailyQuota).filter(DailyQuota.user_id == user_id, DailyQuota.date == today).first()
            if daily_record:
                daily_record.count += 1
                db.add(daily_record)
            else:
                # Should have been created by check_and_reset, but just in case
                new_daily = DailyQuota(user_id=user_id, date=today, count=1)
                db.add(new_daily)
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error reducing quota: {e}")
            db.rollback()
            return False
