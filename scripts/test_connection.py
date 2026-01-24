import sys
import os
import socket

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from app.config import settings

def test_dns():
    print("\n--- Testing DNS Resolution (Skipped for Localhost) ---")
    return True

def test_db_connection():
    print("\n--- Testing Database Connection ---")
    print(f"URL: {settings.DATABASE_URL.split('@')[1]}") # Hide password
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database Connection Successful!")
            print(f"Result: {result.scalar()}")
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")

if __name__ == "__main__":
    if test_dns():
        test_db_connection()
