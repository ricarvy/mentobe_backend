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
        # Check Demo User specifically
        user_id = "00000000-0000-0000-0000-000000000000"
        print(f"Checking Demo User {user_id}...")
        response = supabase.table("users").select("id, email, quota, vip_level, vip_expire_at").eq("id", user_id).execute()
        if response.data:
            print(f"User Data: {response.data[0]}")
        else:
            print("Demo User not found.")
            
        # Check payments for this user
        print(f"\nChecking payments for user {user_id}...")
        payments_resp = supabase.table("payments").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
        if payments_resp.data:
            print(f"Recent Payments ({len(payments_resp.data)}):")
            for p in payments_resp.data:
                print(f" - ID: {p['id']}, Amount: {p.get('amount_total')}, Status: {p['status']}, Created: {p['created_at']}")
        else:
            print("No payments found for this user.")

    except Exception as e:
        print(f"Error accessing users table VIP columns: {e}")

if __name__ == "__main__":
    asyncio.run(main())
