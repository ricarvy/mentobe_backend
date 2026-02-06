from sqlalchemy import create_engine, text
import os

DATABASE_URL = "mysql+pymysql://root:789632145@127.0.0.1:3306/mentobe?charset=utf8mb4"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # 1. Get User Info
        print("--- User Info ---")
        result = conn.execute(text("SELECT id, email, vip_level, vip_expire_at FROM users WHERE email = '597928240@qq.com'"))
        user = result.fetchone()
        if user:
            print(dict(zip(result.keys(), user)))
            user_id = user[0]
            
            # 2. Get Payment Records for this user
            print("\n--- Payment Records ---")
            payments = conn.execute(text(f"SELECT id, stripe_session_id, amount_total, status, price_id, created_at FROM payments WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 5"))
            for row in payments:
                print(dict(zip(payments.keys(), row)))
        else:
            print("User not found")

except Exception as e:
    print("Error connecting to DB:", e)
