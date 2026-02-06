import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.db_models import SystemConfig, User, Payment
from datetime import datetime, timedelta, timezone

def fix_config():
    db = SessionLocal()
    try:
        configs = [
            {
                "key": "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_MONTHLY",
                "value": "price_1SxOoPGVP93aj81TCDnE6Kln",
                "description": "Price ID for Pro to Premium Upgrade (Monthly)"
            },
            {
                "key": "NEXT_PUBLIC_STRIPE_PRICE_UPGRADE_YEARLY",
                "value": "price_1SxOokGVP93aj81T1nGGEiND",
                "description": "Price ID for Pro to Premium Upgrade (Yearly)"
            }
        ]

        print("--- Updating System Config ---")
        for item in configs:
            config = db.query(SystemConfig).filter(SystemConfig.key == item["key"]).first()
            if config:
                config.value = item["value"]
                print(f"Updated {item['key']}")
            else:
                config = SystemConfig(key=item["key"], value=item["value"], description=item["description"])
                db.add(config)
                print(f"Inserted {item['key']}")
        
        db.commit()
        print("Config update complete.")
        
        # --- Fix User ---
        print("\n--- Checking for affected user ---")
        # Search for user starting with d3384bb4
        user = db.query(User).filter(User.id.like("d3384bb4%")).first()
        
        if not user:
            print("User d3384bb4... not found.")
            return

        print(f"Found User: {user.id}")
        print(f"Current VIP Level: {user.vip_level}")
        print(f"Current Expire At: {user.vip_expire_at}")

        # Find recent payment for this user with the upgrade price ID
        # or any payment with vip_level=0 (which indicates failure to map)
        
        # We look for the upgrade price IDs
        upgrade_prices = [c["value"] for c in configs]
        
        payment = db.query(Payment).filter(
            Payment.user_id == user.id,
            Payment.price_id.in_(upgrade_prices)
        ).order_by(Payment.created_at.desc()).first()

        if payment:
            print(f"Found Payment ID: {payment.id}, PriceID: {payment.price_id}, VIP Level in Payment: {payment.vip_level}")
            
            if payment.vip_level != 2:
                print("Correcting Payment VIP Level to 2...")
                payment.vip_level = 2
                payment.vip_duration = "monthly" if payment.price_id == configs[0]["value"] else "yearly"
                db.add(payment)
            
            # Now update User if needed
            if user.vip_level != 2:
                print("Upgrading User to VIP Level 2...")
                user.vip_level = 2
                
                # Calculate expiration
                duration = 30 if payment.price_id == configs[0]["value"] else 365
                now = datetime.now(timezone.utc)
                
                # Logic from stripe.py:
                # If active, extend? Or if upgrade, reset?
                # The user paid for an upgrade. 
                # If they were Pro (level 1), they become Premium (level 2).
                # We'll set it to 30 days from NOW (simplest recovery).
                new_expire = now + timedelta(days=duration)
                
                user.vip_expire_at = new_expire
                user.quota = 999999 # Premium quota
                db.add(user)
                print(f"User updated. New Expire At: {new_expire}")
            else:
                print("User is already VIP Level 2.")
                
            db.commit()
            print("Fix applied successfully.")
            
        else:
            print("No payment found with upgrade price IDs for this user.")
            # Check for any payment with vip_level=0 recently
            payment_failed = db.query(Payment).filter(
                Payment.user_id == user.id,
                Payment.vip_level == 0
            ).order_by(Payment.created_at.desc()).first()
            
            if payment_failed:
                print(f"Found a payment with VIP Level 0: {payment_failed.id}, PriceID: {payment_failed.price_id}")
                if payment_failed.price_id in upgrade_prices:
                    print("This is indeed the upgrade payment.")
                    # Apply fix (same logic as above)
                    payment_failed.vip_level = 2
                    payment_failed.vip_duration = "monthly" if payment_failed.price_id == configs[0]["value"] else "yearly"
                    db.add(payment_failed)
                    
                    user.vip_level = 2
                    duration = 30 if payment_failed.price_id == configs[0]["value"] else 365
                    now = datetime.now(timezone.utc)
                    new_expire = now + timedelta(days=duration)
                    user.vip_expire_at = new_expire
                    user.quota = 999999
                    db.add(user)
                    db.commit()
                    print("Fix applied successfully (via vip_level=0 record).")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_config()
