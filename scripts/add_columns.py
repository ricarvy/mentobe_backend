import sys
import os
from sqlalchemy import text

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine

def add_columns():
    with engine.connect() as conn:
        try:
            print("Adding columns...")
            conn.execute(text("ALTER TABLE tarot_spread_categories ADD COLUMN name_en VARCHAR(100)"))
            conn.execute(text("ALTER TABLE tarot_spread_categories ADD COLUMN name_jp VARCHAR(100)"))
            conn.execute(text("ALTER TABLE tarot_spread_categories ADD COLUMN description_en VARCHAR(255)"))
            conn.execute(text("ALTER TABLE tarot_spread_categories ADD COLUMN description_jp VARCHAR(255)"))
            conn.commit()
            print("Columns added.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

if __name__ == "__main__":
    add_columns()
