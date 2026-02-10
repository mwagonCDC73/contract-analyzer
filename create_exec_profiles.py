#!/usr/bin/env python3
"""
Create user profiles for new executive users
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print('=' * 80)
print('CREATING EXECUTIVE USER PROFILES')
print('=' * 80)

# New users to create
new_users = [
    {
        'email': 'dg@caldrywall.com',
        'full_name': 'David Garrett',
        'role': 'executive'
    },
    {
        'email': 'pg@caldrywall.com',
        'full_name': 'Paul Gutierrez',
        'role': 'executive'
    }
]

# Get all auth users to find their IDs
print('\n1. Fetching user IDs from Supabase Auth...')
try:
    # Use admin API to list users
    auth_users = supabase.auth.admin.list_users()

    print(f'   Found {len(auth_users)} auth users')

    # Create a mapping of email to user ID
    email_to_id = {}
    for user in auth_users:
        if hasattr(user, 'email') and hasattr(user, 'id'):
            email_to_id[user.email] = user.id
            print(f'   - {user.email}: {user.id}')

except Exception as e:
    print(f'   ERROR accessing auth users: {e}')
    print('\n   Using alternative method: checking existing profiles and manual ID entry...')
    email_to_id = {}

print('\n2. Creating user profiles...\n')

for user_data in new_users:
    email = user_data['email']

    # Try to get user ID from auth
    user_id = email_to_id.get(email)

    if not user_id:
        print(f'   WARNING: Could not find auth user ID for {email}')
        print(f'   You may need to manually get the ID from Supabase dashboard')
        continue

    # Check if profile already exists
    try:
        existing = supabase.table('user_profiles').select('*').eq('id', user_id).execute()
        if existing.data:
            print(f'   Profile already exists for {email}')
            # Update the role
            response = supabase.table('user_profiles').update({
                'full_name': user_data['full_name'],
                'role': user_data['role']
            }).eq('id', user_id).execute()
            print(f'   ✓ Updated profile: {user_data["full_name"]} ({email}) - Role: {user_data["role"]}')
            continue
    except Exception as e:
        pass  # Profile doesn't exist, will create it

    # Create new profile
    try:
        profile_data = {
            'id': user_id,
            'email': email,
            'full_name': user_data['full_name'],
            'role': user_data['role']
        }

        response = supabase.table('user_profiles').insert(profile_data).execute()

        if response.data:
            print(f'   ✓ Created profile: {user_data["full_name"]} ({email}) - Role: {user_data["role"]}')
        else:
            print(f'   ✗ Failed to create profile for {email}')

    except Exception as e:
        print(f'   ✗ ERROR creating profile for {email}: {e}')

print('\n' + '=' * 80)
print('VERIFICATION - All Users with Executive/Admin Roles:')
print('=' * 80)

try:
    response = supabase.table('user_profiles').select('*').in_('role', ['executive', 'admin']).execute()

    if response.data:
        for user in response.data:
            print(f"  • {user.get('full_name')} - {user.get('email')} ({user.get('role')})")
    else:
        print('  No executive/admin users found')

except Exception as e:
    print(f'  ERROR: {e}')

print('=' * 80)
