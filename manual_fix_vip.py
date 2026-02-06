from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

DATABASE_URL = "mysql+pymysql://root:789632145@127.0.0.1:3306/mentobe?charset=utf8mb4"

def update_vip():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # 1. Find user
            email = '597928240@qq.com'
            result = conn.execute(text(f"SELECT id FROM users WHERE email = '{email}'"))
            user = result.fetchone()
            
            if not user:
                print(f"User {email} not found")
                return

            user_id = user[0]
            
            # 2. Update VIP
            # Assuming Pro Monthly (Level 1, 30 days)
            new_expire_at = datetime.utcnow() + timedelta(days=30)
            
            conn.execute(text(f"""
                UPDATE users 
                SET vip_level = 1, vip_expire_at = :expire_at, quota = 999999 
                WHERE id = :user_id
            """), {"expire_at": new_expire_at, "user_id": user_id})
            
            conn.commit()
            print(f"Successfully updated VIP for {email}")
            
    except Exception as e:
        print(f"Error updating VIP: {e}")

if __name__ == "__main__":
    update_vip()
