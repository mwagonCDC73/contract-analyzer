"""
Test script to verify the /api/auth/profile endpoint
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://localhost:8000"
TEST_EMAIL = os.getenv("TEST_EMAIL", "matt@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "password123")

def test_profile_endpoint():
    print("=" * 60)
    print("Testing /api/auth/profile endpoint")
    print("=" * 60)

    # Step 1: Login to get access token
    print("\n1. Logging in...")
    login_response = requests.post(
        f"{API_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )

    if login_response.status_code != 200:
        print(f"[FAIL] Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        return

    login_data = login_response.json()
    access_token = login_data.get("access_token")
    print(f"[OK] Login successful")
    print(f"   Token: {access_token[:20]}...")

    # Step 2: Test /api/auth/me endpoint
    print("\n2. Testing /api/auth/me...")
    me_response = requests.get(
        f"{API_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if me_response.status_code == 200:
        print(f"[OK] /api/auth/me works")
        print(f"   Response: {me_response.json()}")
    else:
        print(f"[FAIL] /api/auth/me failed: {me_response.status_code}")
        print(f"   Response: {me_response.text}")

    # Step 3: Test /api/auth/profile endpoint
    print("\n3. Testing /api/auth/profile...")
    profile_response = requests.get(
        f"{API_URL}/api/auth/profile",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if profile_response.status_code == 200:
        print(f"[OK] /api/auth/profile works!")
        print(f"   Response: {profile_response.json()}")
    else:
        print(f"[FAIL] /api/auth/profile failed: {profile_response.status_code}")
        print(f"   Response: {profile_response.text}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_profile_endpoint()
