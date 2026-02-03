import os
import sys
from sqlalchemy import create_engine, text
from app.config import settings

# Adjust python path
sys.path.append(os.getcwd())

def add_column():
    print("Connecting to database...")
    # Use DATABASE_URL from environment or config
    database_url = settings.DATABASE_URL
    if not database_url:
        print("DATABASE_URL not set!")
        sys.exit(1)
        
    engine = create_engine(database_url)
    
    # Check if column exists
    check_sql = text("""
        SELECT count(*) 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'login_token_updated_at';
    """)
    
    add_sql = text("ALTER TABLE users ADD COLUMN login_token_updated_at DATETIME;")
    
    with engine.connect() as conn:
        result = conn.execute(check_sql).scalar()
        if result == 0:
            print("Adding 'login_token_updated_at' column to 'users' table...")
            conn.execute(add_sql)
            conn.commit() # Important for some DBs
            print("Column added successfully.")
        else:
            print("Column 'login_token_updated_at' already exists.")

if __name__ == "__main__":
    add_column()
