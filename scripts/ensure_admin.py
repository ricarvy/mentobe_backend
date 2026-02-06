import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.db_models import AdminUser
from app.dependencies import get_password_hash

def ensure_admin():
    db = SessionLocal()
    try:
        username = "admin@mentobe.com"
        password = "adminpassword"
        
        admin = db.query(AdminUser).filter(AdminUser.username == username).first()
        if not admin:
            print(f"Creating admin user: {username}")
            new_admin = AdminUser(
                username=username,
                password=get_password_hash(password),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            print("Admin user created.")
        else:
            print(f"Admin user {username} already exists.")
            # Verify password? No, just leave it.
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    ensure_admin()
