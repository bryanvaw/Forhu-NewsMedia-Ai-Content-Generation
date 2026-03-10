import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")


def test_supabase_connection():
    try:
        # Initialize client
        supabase: Client = create_client(url, key)

        # Test connection by fetching 1 row from any table
        # (or just checking if the client object initializes)
        print(f"Connecting to: {url}...")

        # This checks if we can at least reach the API
        response = supabase.table("raw_articles").select("count", count="exact").limit(1).execute()

        print("✅ Connection Successful!")
        print(f"Found {response.count} total raw articles in the database.")
        return supabase
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return None


if __name__ == "__main__":
    test_supabase_connection()