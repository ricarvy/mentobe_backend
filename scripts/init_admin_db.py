import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db_models import AdminUser, User
from app.dependencies import get_password_hash
from datetime import datetime

def init_admin(env_file):
    print(f"Loading environment from {env_file}...")
    load_dotenv(env_file)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in environment.")
        return

    print(f"Connecting to database: {database_url.split('@')[1]}") # Mask password
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    admin_username = "admin@mentobe.com"
    password = "adminpassword"
    
    try:
        # 1. Check/Create AdminUser
        print(f"Checking AdminUser: {admin_username}")
        admin = db.query(AdminUser).filter(AdminUser.username == admin_username).first()
        if admin:
            print("AdminUser already exists.")
            # Optional: Reset password if needed
            # admin.password = get_password_hash(password)
            # db.add(admin)
            # print("Admin password reset.")
        else:
            print("Creating AdminUser...")
            new_admin = AdminUser(
                username=admin_username,
                password=get_password_hash(password),
                role="admin"
            )
            db.add(new_admin)
            print("AdminUser created.")

        # 2. Check/Create User (for consistency)
        print(f"Checking User: {admin_username}")
        user = db.query(User).filter(User.email == admin_username).first()
        if user:
            print("User entry already exists.")
        else:
            print("Creating User entry...")
            new_user = User(
                email=admin_username,
                password=get_password_hash(password),
                username="Admin",
                is_active=True,
                created_at=datetime.now(),
                quota=999999,
                vip_level=99
            )
            db.add(new_user)
            print("User entry created.")
            
        db.commit()
        print("✅ Initialization complete successfully.")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/init_admin_db.py <path_to_env_file>")
        print("Example: python scripts/init_admin_db.py .env.oversea.prod")
        sys.exit(1)
        
    init_admin(sys.argv[1])
