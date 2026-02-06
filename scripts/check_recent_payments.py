from app.database import SessionLocal
from app.db_models import Payment

def list_recent_payments():
    db = SessionLocal()
    try:
        payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(5).all()
        print(f"{'ID':<5} {'User ID':<36} {'Amount':<10} {'Currency':<10} {'Status':<10} {'Created At'}")
        print("-" * 100)
        for p in payments:
            print(f"{p.id:<5} {p.user_id:<36} {p.amount_total:<10} {p.currency:<10} {p.status:<10} {p.created_at}")
    finally:
        db.close()

if __name__ == "__main__":
    list_recent_payments()
