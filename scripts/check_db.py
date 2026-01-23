import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.db_models import User, Payment
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        print("Checking 'payments' table...")
        # Try to select from payments table
        payments = db.query(Payment).limit(1).all()
        print("Payments table exists.")
        if payments:
            for p in payments:
                print(f"Data: ID={p.id}, Amount={p.amount_total}, Status={p.status}")
        else:
            print("No payments found yet.")

        print("\nChecking 'users' table columns...")
        # Check Demo User specifically
        user_id = "00000000-0000-0000-0000-000000000000"
        print(f"Checking Demo User {user_id}...")
        
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            print(f"User Data: ID={user.id}, Email={user.email}, Quota={user.quota}, VIP Level={user.vip_level}, Expire={user.vip_expire_at}")
        else:
            print("Demo User not found.")
            
        # Check payments for this user
        print(f"\nChecking payments for user {user_id}...")
        user_payments = db.query(Payment).filter(Payment.user_id == user_id).order_by(Payment.created_at.desc()).limit(5).all()
        
        if user_payments:
            print(f"Recent Payments ({len(user_payments)}):")
            for p in user_payments:
                print(f" - ID: {p.id}, Amount: {p.amount_total}, Status: {p.status}, Created: {p.created_at}")
        else:
            print("No payments found for this user.")

    except Exception as e:
        print(f"Error accessing database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
