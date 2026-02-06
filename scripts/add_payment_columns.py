from app.database import engine
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE payments ADD COLUMN payment_intent_id VARCHAR(255) NULL"))
            print("Added payment_intent_id column")
        except Exception as e:
            print(f"Skipping payment_intent_id: {e}")

        try:
            conn.execute(text("ALTER TABLE payments ADD COLUMN subscription_id VARCHAR(255) NULL"))
            print("Added subscription_id column")
        except Exception as e:
            print(f"Skipping subscription_id: {e}")

        try:
            conn.execute(text("ALTER TABLE payments ADD COLUMN invoice_id VARCHAR(255) NULL"))
            print("Added invoice_id column")
        except Exception as e:
            print(f"Skipping invoice_id: {e}")
            
        conn.commit()

if __name__ == "__main__":
    add_columns()