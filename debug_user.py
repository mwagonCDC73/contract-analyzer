#!/usr/bin/env python3
"""
Debug user profile lookup for dg@caldrywall.com
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print('=' * 80)
print('DEBUGGING USER PROFILE LOOKUP')
print('=' * 80)

email = 'dg@caldrywall.com'
expected_id = 'e2fb3bea-df22-409b-a56a-6ee57cd402ed'

print(f'\nLooking for user: {email}')
print(f'Expected auth ID: {expected_id}')

# 1. Check if profile exists by ID
print('\n1. Lookup by ID:')
try:
    response = supabase.table('user_profiles').select('*').eq('id', expected_id).execute()
    if response.data:
        print(f'   [OK] Found profile by ID')
        for key, value in response.data[0].items():
            print(f'   - {key}: {value}')
    else:
        print(f'   [ERROR] No profile found with ID: {expected_id}')
except Exception as e:
    print(f'   [ERROR] Exception: {e}')

# 2. Check if profile exists by email
print('\n2. Lookup by email:')
try:
    response = supabase.table('user_profiles').select('*').eq('email', email).execute()
    if response.data:
        print(f'   [OK] Found {len(response.data)} profile(s) by email')
        for profile in response.data:
            print(f'   Profile ID: {profile.get("id")}')
            print(f'   Full Name: {profile.get("full_name")}')
            print(f'   Role: {profile.get("role")}')
            print(f'   Email: {profile.get("email")}')

            if profile.get('id') != expected_id:
                print(f'   [WARNING] Profile ID mismatch!')
                print(f'             Profile has: {profile.get("id")}')
                print(f'             Auth expects: {expected_id}')
    else:
        print(f'   [ERROR] No profile found with email: {email}')
except Exception as e:
    print(f'   [ERROR] Exception: {e}')

# 3. Try to authenticate and get the actual auth user ID
print('\n3. Check what auth system returns:')
print('   (This will require the actual password)')
print(f'   You would call: supabase.auth.sign_in_with_password(email={email}, password=...)')
print('   And check: response.user.id')

print('\n' + '=' * 80)
print('RECOMMENDATION:')
print('=' * 80)
print('If the IDs do not match, we need to either:')
print('  A) Delete the profile with wrong ID and recreate it')
print('  B) Update the profile ID to match the auth user ID')
print('=' * 80)
