#!/usr/bin/env python3
"""
List all users and identify those with executive permissions
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print('=' * 80)
print('USERS WITH EXECUTIVE PERMISSIONS')
print('=' * 80)

# Get all users
try:
    response = supabase.table('user_profiles').select('*').execute()

    if response.data:
        print(f'\nTotal users found: {len(response.data)}\n')

        for user in response.data:
            role = user.get('role', 'unknown')
            print(f"User: {user.get('full_name')}")
            print(f"  Email: {user.get('email')}")
            print(f"  Role: {role}")
            print(f"  ID: {user.get('id')}")
            print()

        # Filter executives
        executives = [u for u in response.data if u.get('role') in ['executive', 'admin']]
        print('=' * 80)
        print(f'EXECUTIVES/ADMINS: {len(executives)}')
        print('=' * 80)

        if executives:
            for exec_user in executives:
                print(f"{exec_user.get('full_name')} - {exec_user.get('email')} ({exec_user.get('role')})")
        else:
            print('No users with executive or admin role found')
            print('\nNote: The exec_review.py login form shows placeholder: exec.test@caldrywall.com')
            print('You may need to create an executive user in the database.')
    else:
        print('No users found in database')

except Exception as e:
    print(f'ERROR: {e}')
