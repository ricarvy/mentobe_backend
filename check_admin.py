import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to sys.path to ensure we can import app modules if needed
# But for this script, we'll try to be standalone or use minimal imports
sys.path.append(os.getcwd())

from app.database import Base
from app.models import User, AdminUser
from app.core.security import get_password_hash

# Get DATABASE_URL from environment or use the one from .env.prod manually if needed
# We assume this script runs in an environment where DATABASE_URL is set
# or we read it from .env.prod
from dotenv import load_dotenv
load_dotenv('.env.prod')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment or .env.prod")
    sys.exit(1)

print(f"Connecting to database...")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_and_create_admin():
    db = SessionLocal()
    try:
        # Check AdminUser table
        print("Checking AdminUser table...")
        admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if admin:
            print("Admin user 'admin' already exists.")
        else:
            print("Admin user 'admin' not found. Creating...")
            hashed_password = get_password_hash("admin")
            new_admin = AdminUser(
                username="admin",
                hashed_password=hashed_password,
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            print("Admin user 'admin' created successfully with password 'admin'.")
            
    except Exception as e:
        print(f"Error: {e}")
        # Try to verify connection
        try:
            db.execute(text("SELECT 1"))
            print("Database connection is active.")
        except Exception as conn_err:
            print(f"Database connection failed: {conn_err}")
    finally:
        db.close()

if __name__ == "__main__":
    check_and_create_admin()
