from sqlalchemy import create_engine, text
import os

# Load from .env.local manually if needed, or just hardcode for this check
DATABASE_URL = "mysql+pymysql://root:789632145@127.0.0.1:3306/mentobe?charset=utf8mb4"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, email, vip_level FROM users LIMIT 5"))
        users = [dict(zip(result.keys(), row)) for row in result]
        print("Users found:", users)
except Exception as e:
    print("Error connecting to DB:", e)
