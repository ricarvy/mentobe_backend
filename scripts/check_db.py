import asyncio
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

async def main():
    print("Checking 'payments' table...")
    try:
        # Try to select from payments table
        response = supabase.table("payments").select("*").limit(1).execute()
        print("Payments table exists.")
        print(f"Data: {response.data}")
    except Exception as e:
        print(f"Error accessing payments table: {e}")

    print("\nChecking 'users' table columns...")
    try:
        # Try to select new columns from users table
        response = supabase.table("users").select("id, vip_level, vip_expire_at").limit(1).execute()
        print("Users table has VIP columns.")
        print(f"Data: {response.data}")
    except Exception as e:
        print(f"Error accessing users table VIP columns: {e}")

if __name__ == "__main__":
    asyncio.run(main())
