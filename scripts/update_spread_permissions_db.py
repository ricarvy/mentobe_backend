import sys
import os
from sqlalchemy.orm import Session

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.db_models import TarotSpread

def update_permissions():
    db = SessionLocal()
    try:
        spreads = db.query(TarotSpread).all()
        print(f"Found {len(spreads)} spreads. Updating permissions...")
        
        for spread in spreads:
            count = spread.card_count
            old_perm = spread.permission
            new_perm = old_perm
            
            # Logic:
            # < 3 cards (1-2): Free
            # 3-6 cards: Pro
            # > 6 cards: Premium
            
            if count < 3:
                new_perm = "Free"
            elif 3 <= count <= 6:
                new_perm = "Pro"
            else:
                new_perm = "Premium"
            
            if old_perm != new_perm:
                print(f"Updating '{spread.name}' ({count} cards): {old_perm} -> {new_perm}")
                spread.permission = new_perm
            else:
                print(f"Skipping '{spread.name}' ({count} cards): Already {new_perm}")
        
        db.commit()
        print("Permissions updated successfully.")
        
    except Exception as e:
        print(f"Error updating permissions: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_permissions()
