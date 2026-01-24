import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.db_models import User
from app.dependencies import get_password_hash
from datetime import datetime

def main():
    db = SessionLocal()
    try:
        # Check if admin exists
        # We use "admin" as email to allow login with "admin"
        admin_email = "admin"
        admin = db.query(User).filter(User.email == admin_email).first()
        
        if admin:
            print("Admin user already exists.")
            # Optional: update password/permissions if needed
            # admin.password = get_password_hash("admin")
            # admin.vip_level = 99
            # db.commit()
            return

        print("Creating admin user...")
        new_admin = User(
            email=admin_email,
            password=get_password_hash("admin"),
            username="Administrator",
            is_active=True,
            created_at=datetime.now(),
            quota=999999,
            vip_level=99, # 99 = Admin
            vip_expire_at=datetime(2099, 12, 31)
        )
        
        db.add(new_admin)
        db.commit()
        print("✅ Admin user created successfully.")
        print("Username: admin")
        print("Password: admin")
        
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
