#!/usr/bin/env python3
"""
Test login for dg@caldrywall.com to see what auth returns
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import getpass

load_dotenv(override=True)
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print('=' * 80)
print('TEST LOGIN FOR dg@caldrywall.com')
print('=' * 80)

email = 'dg@caldrywall.com'
password = getpass.getpass('Enter password for dg@caldrywall.com: ')

print('\n1. Attempting authentication...')
try:
    auth_response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

    print('[OK] Authentication successful!')
    print(f'\nAuth Response type: {type(auth_response)}')
    print(f'Has user attribute: {hasattr(auth_response, "user")}')

    if hasattr(auth_response, 'user') and auth_response.user:
        print(f'\nUser object type: {type(auth_response.user)}')
        print(f'User ID: {auth_response.user.id}')
        print(f'User ID type: {type(auth_response.user.id)}')
        print(f'User email: {auth_response.user.email if hasattr(auth_response.user, "email") else "N/A"}')

        # Try to fetch profile
        user_id = auth_response.user.id
        print(f'\n2. Fetching user profile for ID: {user_id}...')

        try:
            response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            print(f'[OK] Profile fetch successful!')
            print(f'Profile data: {response.data}')
        except Exception as e:
            print(f'[ERROR] Profile fetch failed: {e}')

    else:
        print('[ERROR] No user in auth response')

except Exception as e:
    print(f'[ERROR] Authentication failed: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '=' * 80)
