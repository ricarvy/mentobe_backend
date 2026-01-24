# from supabase import create_client, Client
from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Initialize Supabase client
# supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Initialize SQLAlchemy
engine = create_engine(settings.DATABASE_URL)
print(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

