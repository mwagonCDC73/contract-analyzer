"""
Test script to debug API issues
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=== Environment Variables ===")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')[:50]}..." if os.getenv('SUPABASE_URL') else "SUPABASE_URL: Not set")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')[:20]}..." if os.getenv('SUPABASE_KEY') else "SUPABASE_KEY: Not set")
print(f"ANTHROPIC_API_KEY: {os.getenv('ANTHROPIC_API_KEY')[:20]}..." if os.getenv('ANTHROPIC_API_KEY') else "ANTHROPIC_API_KEY: Not set")

print("\n=== Testing Supabase Connection ===")
try:
    from services.supabase import get_supabase_client
    client = get_supabase_client()
    print("[OK] Supabase client created successfully")

    # Test query
    result = client.table('projects').select('*').limit(1).execute()
    print(f"[OK] Query executed successfully")
    print(f"  Result: {len(result.data)} rows")
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Testing Auth Token Validation ===")
# This would need an actual token to test
print("Skipping - requires valid token")
