#!/usr/bin/env python3
"""
Database Cleanup Script - California Drywall Contract Review System
WARNING: This script will DELETE data permanently!
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import sys

load_dotenv(override=True)
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print('=' * 80)
print('DATABASE CLEANUP SCRIPT')
print('=' * 80)
print()
print('This script can delete:')
print('  1. All projects and their contracts')
print('  2. All red flags')
print('  3. All files from storage')
print('  4. Everything (full reset)')
print('  5. Delete specific project by ID')
print('  6. Delete projects by status (draft, submitted, etc.)')
print('  7. Cancel')
print()

choice = input('Enter your choice (1-7): ').strip()

def delete_all_red_flags():
    """Delete all red flags"""
    try:
        response = supabase.table('red_flags').select('id').execute()
        count = len(response.data) if response.data else 0

        if count > 0:
            confirm = input(f'Delete {count} red flags? (yes/no): ')
            if confirm.lower() == 'yes':
                supabase.table('red_flags').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                print(f'[OK] Deleted {count} red flags')
        else:
            print('[INFO] No red flags found')
    except Exception as e:
        print(f'[ERROR] Failed to delete red flags: {e}')


def delete_all_contracts():
    """Delete all contracts"""
    try:
        response = supabase.table('contracts').select('id').execute()
        count = len(response.data) if response.data else 0

        if count > 0:
            confirm = input(f'Delete {count} contracts? (yes/no): ')
            if confirm.lower() == 'yes':
                supabase.table('contracts').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                print(f'[OK] Deleted {count} contracts')
        else:
            print('[INFO] No contracts found')
    except Exception as e:
        print(f'[ERROR] Failed to delete contracts: {e}')


def delete_all_projects():
    """Delete all projects"""
    try:
        response = supabase.table('projects').select('id, project_name').execute()
        count = len(response.data) if response.data else 0

        if count > 0:
            print(f'\nFound {count} projects:')
            for p in response.data:
                print(f"  - {p.get('project_name')} (ID: {p.get('id')})")

            confirm = input(f'\nDelete all {count} projects? (yes/no): ')
            if confirm.lower() == 'yes':
                supabase.table('projects').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                print(f'[OK] Deleted {count} projects')
        else:
            print('[INFO] No projects found')
    except Exception as e:
        print(f'[ERROR] Failed to delete projects: {e}')


def delete_storage_files():
    """Delete all files from storage"""
    try:
        response = supabase.storage.from_('contracts').list()

        if response:
            count = len(response)
            print(f'\nFound {count} folders/files in storage')
            confirm = input(f'Delete all storage contents? (yes/no): ')
            if confirm.lower() == 'yes':
                for item in response:
                    try:
                        # List files in folder
                        folder_name = item.get('name')
                        files = supabase.storage.from_('contracts').list(folder_name)

                        # Delete each file
                        for file in files:
                            file_path = f"{folder_name}/{file.get('name')}"
                            supabase.storage.from_('contracts').remove([file_path])
                            print(f'  Deleted: {file_path}')
                    except:
                        pass

                print(f'[OK] Deleted storage contents')
        else:
            print('[INFO] No storage files found')
    except Exception as e:
        print(f'[ERROR] Failed to delete storage files: {e}')


def delete_project_by_id(project_id):
    """Delete a specific project and all its data"""
    try:
        # Get project info
        project = supabase.table('projects').select('*').eq('id', project_id).execute()
        if not project.data:
            print(f'[ERROR] Project {project_id} not found')
            return

        project_name = project.data[0].get('project_name')
        print(f'\nProject: {project_name}')

        # Get contracts
        contracts = supabase.table('contracts').select('id, file_path').eq('project_id', project_id).execute()
        contract_count = len(contracts.data) if contracts.data else 0

        # Get red flags
        red_flag_count = 0
        if contracts.data:
            for contract in contracts.data:
                flags = supabase.table('red_flags').select('id').eq('contract_id', contract['id']).execute()
                red_flag_count += len(flags.data) if flags.data else 0

        print(f'  Contracts: {contract_count}')
        print(f'  Red flags: {red_flag_count}')

        confirm = input(f'\nDelete this project and all its data? (yes/no): ')
        if confirm.lower() == 'yes':
            # Delete red flags
            if contracts.data:
                for contract in contracts.data:
                    supabase.table('red_flags').delete().eq('contract_id', contract['id']).execute()

                    # Delete storage file
                    if contract.get('file_path'):
                        try:
                            supabase.storage.from_('contracts').remove([contract['file_path']])
                        except:
                            pass

            # Delete contracts
            supabase.table('contracts').delete().eq('project_id', project_id).execute()

            # Delete project
            supabase.table('projects').delete().eq('id', project_id).execute()

            print(f'[OK] Deleted project: {project_name}')
    except Exception as e:
        print(f'[ERROR] Failed to delete project: {e}')


def delete_projects_by_status(status):
    """Delete all projects with a specific status"""
    try:
        response = supabase.table('projects').select('id, project_name, status').eq('status', status).execute()
        count = len(response.data) if response.data else 0

        if count > 0:
            print(f'\nFound {count} projects with status "{status}":')
            for p in response.data:
                print(f"  - {p.get('project_name')} (ID: {p.get('id')})")

            confirm = input(f'\nDelete all {count} projects with status "{status}"? (yes/no): ')
            if confirm.lower() == 'yes':
                for project in response.data:
                    delete_project_by_id(project['id'])
                print(f'[OK] Deleted {count} projects')
        else:
            print(f'[INFO] No projects found with status "{status}"')
    except Exception as e:
        print(f'[ERROR] Failed to delete projects: {e}')


# Execute based on choice
if choice == '1':
    print('\n--- DELETE ALL PROJECTS AND CONTRACTS ---')
    delete_all_red_flags()
    delete_all_contracts()
    delete_all_projects()

elif choice == '2':
    print('\n--- DELETE ALL RED FLAGS ---')
    delete_all_red_flags()

elif choice == '3':
    print('\n--- DELETE ALL STORAGE FILES ---')
    delete_storage_files()

elif choice == '4':
    print('\n--- FULL DATABASE RESET ---')
    print('WARNING: This will delete EVERYTHING!')
    final_confirm = input('Type "DELETE EVERYTHING" to confirm: ')
    if final_confirm == 'DELETE EVERYTHING':
        delete_all_red_flags()
        delete_all_contracts()
        delete_all_projects()
        delete_storage_files()
        print('\n[OK] Database completely reset')
    else:
        print('[CANCELLED] Full reset cancelled')

elif choice == '5':
    print('\n--- DELETE SPECIFIC PROJECT ---')
    project_id = input('Enter project ID (UUID): ').strip()
    if project_id:
        delete_project_by_id(project_id)
    else:
        print('[ERROR] Invalid project ID')

elif choice == '6':
    print('\n--- DELETE PROJECTS BY STATUS ---')
    print('Available statuses: draft, submitted, under_review, approved, rejected')
    status = input('Enter status: ').strip()
    if status:
        delete_projects_by_status(status)
    else:
        print('[ERROR] Invalid status')

elif choice == '7':
    print('[CANCELLED] No changes made')

else:
    print('[ERROR] Invalid choice')

print('\n' + '=' * 80)
print('CLEANUP COMPLETE')
print('=' * 80)
