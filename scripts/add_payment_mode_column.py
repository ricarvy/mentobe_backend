from app.database import SessionLocal, engine
from sqlalchemy import text

def add_mode_column():
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("SHOW COLUMNS FROM payments LIKE 'mode'"))
        if result.fetchone():
            print("Column 'mode' already exists.")
        else:
            print("Adding column 'mode' to payments table...")
            db.execute(text("ALTER TABLE payments ADD COLUMN mode VARCHAR(20)"))
            print("Column added successfully.")
            
            # Backfill existing records
            print("Backfilling existing records...")
            # If subscription_id exists, it's subscription, else payment
            db.execute(text("UPDATE payments SET mode = 'subscription' WHERE subscription_id IS NOT NULL"))
            db.execute(text("UPDATE payments SET mode = 'payment' WHERE subscription_id IS NULL"))
            print("Backfill complete.")
            
            db.commit()
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_mode_column()
