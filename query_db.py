#!/usr/bin/env python3
"""
Query the database to check what contract submissions and analysis were saved
"""

import os
import json
from dotenv import load_dotenv
load_dotenv(override=True)

from supabase import create_client

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("ERROR: Missing Supabase credentials")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

print("=" * 80)
print("DATABASE QUERY: Recent Contract Submissions")
print("=" * 80)

# Query 1: Get most recent projects
print("\n1. RECENT PROJECTS")
print("-" * 80)
try:
    projects_response = supabase.table("projects").select("*").order("created_at", desc=True).limit(5).execute()

    if projects_response.data:
        for idx, project in enumerate(projects_response.data, 1):
            print(f"\nProject #{idx}:")
            print(f"  ID: {project.get('id')}")
            print(f"  Name: {project.get('project_name')}")
            print(f"  Number: {project.get('project_number')}")
            print(f"  Status: {project.get('status')}")
            print(f"  PM ID: {project.get('project_manager_id')}")
            print(f"  Created: {project.get('created_at')}")
            print(f"  Submitted: {project.get('submitted_at')}")
    else:
        print("No projects found")
except Exception as e:
    print(f"ERROR querying projects: {e}")
    exit(1)

# Query 2: Get contracts for most recent project
print("\n\n2. CONTRACTS (for most recent project)")
print("-" * 80)
contracts_response = None
try:
    if projects_response.data:
        latest_project_id = projects_response.data[0]['id']
        print(f"Querying contracts for project: {latest_project_id}\n")

        contracts_response = supabase.table("contracts").select("*").eq("project_id", latest_project_id).execute()

        if contracts_response.data:
            for idx, contract in enumerate(contracts_response.data, 1):
                print(f"\nContract #{idx}:")
                print(f"  ID: {contract.get('id')}")
                print(f"  Type: {contract.get('contract_type')}")
                print(f"  File: {contract.get('file_name')}")
                print(f"  Analysis Status: {contract.get('analysis_status')}")
                print(f"  Analysis Date: {contract.get('analysis_date')}")
                print(f"  Created: {contract.get('created_at')}")

                # Check if analysis results exist
                analysis_results = contract.get('analysis_results')
                if analysis_results:
                    print(f"  Analysis Results: ✓ Saved")
                    if isinstance(analysis_results, dict):
                        summary = analysis_results.get('summary', {})
                        print(f"    - Total Issues: {summary.get('total_issues', 'N/A')}")
                        print(f"    - Critical: {summary.get('critical', 'N/A')}")
                        print(f"    - Warning: {summary.get('warning', 'N/A')}")
                        print(f"    - Informational: {summary.get('informational', 'N/A')}")

                        findings = analysis_results.get('findings', [])
                        print(f"    - Findings: {len(findings)} items")
                else:
                    print(f"  Analysis Results: ✗ Not saved")
        else:
            print("No contracts found for this project")
    else:
        print("No projects to query")
except Exception as e:
    print(f"ERROR querying contracts: {e}")

# Query 3: Get red flags for most recent contracts
print("\n\n3. RED FLAGS (individual findings)")
print("-" * 80)
try:
    if contracts_response and contracts_response.data:
        for contract in contracts_response.data:
            contract_id = contract.get('id')
            contract_type = contract.get('contract_type')

            print(f"\nRed Flags for {contract_type} contract ({contract_id}):")

            red_flags_response = supabase.table("red_flags").select("*").eq("contract_id", contract_id).execute()

            if red_flags_response.data:
                print(f"  Found {len(red_flags_response.data)} red flags\n")

                for idx, flag in enumerate(red_flags_response.data[:5], 1):  # Show first 5
                    print(f"  Flag #{idx}:")
                    print(f"    Category: {flag.get('category')}")
                    print(f"    Severity: {flag.get('severity')}")
                    print(f"    Issue: {flag.get('issue_title')}")
                    print(f"    Location: {flag.get('location')}")
                    print(f"    Review Status: {flag.get('review_status')}")
                    print()

                if len(red_flags_response.data) > 5:
                    print(f"  ... and {len(red_flags_response.data) - 5} more red flags")
            else:
                print("  No red flags found")
    else:
        print("No contracts to query")
except Exception as e:
    print(f"ERROR querying red flags: {e}")

# Query 4: Get full analysis JSON for display
print("\n\n4. FULL ANALYSIS JSON (latest contract)")
print("-" * 80)
try:
    if contracts_response and contracts_response.data:
        latest_contract = contracts_response.data[0]
        analysis_results = latest_contract.get('analysis_results')

        if analysis_results:
            print("\nAnalysis JSON Preview:")
            print(json.dumps(analysis_results, indent=2)[:2000])  # First 2000 chars
            print("\n... (truncated)")

            # Save to file for review
            output_file = "latest_analysis.json"
            with open(output_file, "w") as f:
                json.dump(analysis_results, f, indent=2)
            print(f"\n✓ Full analysis saved to: {output_file}")
        else:
            print("No analysis results found")
    else:
        print("No contracts to query")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
if projects_response and projects_response.data:
    print(f"Projects found: {len(projects_response.data)}")
if contracts_response and contracts_response.data:
    print(f"Contracts found: {len(contracts_response.data)}")
    total_flags = 0
    for c in contracts_response.data:
        flags = supabase.table("red_flags").select("id").eq("contract_id", c['id']).execute()
        if flags.data:
            total_flags += len(flags.data)
    print(f"Red flags found: {total_flags}")
print("=" * 80)
