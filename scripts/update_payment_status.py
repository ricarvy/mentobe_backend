from app.database import SessionLocal
from app.db_models import Payment

def update_payment_status(payment_id, new_status):
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            print(f"Updating Payment {payment_id} status from '{payment.status}' to '{new_status}'")
            payment.status = new_status
            db.commit()
            print("Update successful.")
        else:
            print(f"Payment {payment_id} not found.")
    finally:
        db.close()

if __name__ == "__main__":
    update_payment_status(26, "refunded")
