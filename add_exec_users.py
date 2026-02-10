#!/usr/bin/env python3
"""
Add executive user profiles for David Garrett and Paul Gutierrez
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print('=' * 80)
print('ADDING EXECUTIVE USER PROFILES')
print('=' * 80)

# User profile data with UUIDs
users_to_create = [
    {
        'id': 'e2fb3bea-df22-409b-a56a-6ee57cd402ed',
        'email': 'dg@caldrywall.com',
        'full_name': 'David Garrett',
        'role': 'executive'
    },
    {
        'id': '2159ac3f-b21c-4bb1-a79b-1de2346f9000',
        'email': 'pg@caldrywall.com',
        'full_name': 'Paul Gutierrez',
        'role': 'executive'
    }
]

print('\nCreating profiles...\n')

for user_data in users_to_create:
    try:
        # Check if profile already exists
        existing = supabase.table('user_profiles').select('*').eq('id', user_data['id']).execute()

        if existing.data:
            print(f'[!] Profile already exists for {user_data["email"]}')
            # Update the profile
            response = supabase.table('user_profiles').update({
                'full_name': user_data['full_name'],
                'email': user_data['email'],
                'role': user_data['role']
            }).eq('id', user_data['id']).execute()
            print(f'[OK] Updated: {user_data["full_name"]} ({user_data["email"]}) - Role: {user_data["role"]}')
        else:
            # Create new profile
            response = supabase.table('user_profiles').insert(user_data).execute()

            if response.data:
                print(f'[OK] Created: {user_data["full_name"]} ({user_data["email"]}) - Role: {user_data["role"]}')
            else:
                print(f'[ERROR] Failed to create profile for {user_data["email"]}')

    except Exception as e:
        print(f'[ERROR] for {user_data["email"]}: {e}')

print('\n' + '=' * 80)
print('VERIFICATION - All Executive/Admin Users:')
print('=' * 80 + '\n')

try:
    response = supabase.table('user_profiles').select('*').in_('role', ['executive', 'admin']).execute()

    if response.data:
        for user in response.data:
            print(f"  - {user.get('full_name')} - {user.get('email')} ({user.get('role')})")
            print(f"    ID: {user.get('id')}")
            print()
    else:
        print('  No executive/admin users found')

except Exception as e:
    print(f'  ERROR: {e}')

print('=' * 80)
print('DONE! These users can now log in to the executive dashboard:')
print('  Command: streamlit run exec_review.py')
print('=' * 80)
