import sys
import os

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
# Import all models to ensure they are registered with Base
from app.db_models import User, AdminUser, Payment, DailyQuota, TarotInterpretation, SystemConfig, TarotSpreadCategory

def update_schema():
    print("Updating database schema...")
    # This will create any tables that don't exist
    Base.metadata.create_all(bind=engine)
    print("Database schema updated.")

if __name__ == "__main__":
    update_schema()
