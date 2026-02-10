"""
Complete data wipe script.
Deletes ALL contracts, analyses, red flags, projects, and storage files.
Keeps user_profiles and auth data intact.
"""
import os
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "api", ".env"))

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

results = {}

# --- Discover what tables have data ---
TABLES_TO_CHECK = [
    "red_flags",
    "analyses",
    "contracts",
    "projects",
    "user_profiles",  # read-only, just count
]

print("=" * 60)
print("PHASE 1: INVENTORY — Counting rows in all tables")
print("=" * 60)

for table in TABLES_TO_CHECK:
    try:
        resp = supabase.table(table).select("id").execute()
        count = len(resp.data) if resp.data else 0
        results[table] = {"before": count, "deleted": 0}
        print(f"  {table:20s} → {count} rows")
    except Exception as e:
        err_str = str(e)
        if "42P01" in err_str:
            print(f"  {table:20s} → TABLE DOES NOT EXIST")
            results[table] = {"before": 0, "deleted": 0, "missing": True}
        else:
            print(f"  {table:20s} → ERROR: {e}")
            results[table] = {"before": 0, "deleted": 0, "error": str(e)}

# --- Check storage bucket ---
print()
print("Checking storage bucket 'contracts'...")
storage_files = []
try:
    listed = supabase.storage.from_("contracts").list()
    # This lists top-level items (folders/files). Need to recurse into folders.
    for item in (listed or []):
        if item.get("id") is None:
            # It's a folder, list inside it
            folder_name = item["name"]
            try:
                inner = supabase.storage.from_("contracts").list(folder_name)
                for f in (inner or []):
                    if f.get("id") is not None:
                        storage_files.append(f"{folder_name}/{f['name']}")
            except Exception:
                pass
        else:
            storage_files.append(item["name"])
    print(f"  Storage files found: {len(storage_files)}")
except Exception as e:
    print(f"  Storage error: {e}")

print()
print("=" * 60)
print("PHASE 2: DELETING DATA (keeping user_profiles)")
print("=" * 60)

# 1. Delete red_flags
table = "red_flags"
if results.get(table, {}).get("before", 0) > 0 and not results[table].get("missing"):
    try:
        resp = supabase.table(table).select("id").execute()
        ids = [r["id"] for r in resp.data]
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            supabase.table(table).delete().in_("id", batch).execute()
        results[table]["deleted"] = len(ids)
        print(f"  DELETED {len(ids)} rows from {table}")
    except Exception as e:
        print(f"  ERROR deleting {table}: {e}")
else:
    print(f"  {table}: nothing to delete")

# 2. Delete analyses
table = "analyses"
if results.get(table, {}).get("before", 0) > 0 and not results[table].get("missing"):
    try:
        resp = supabase.table(table).select("id").execute()
        ids = [r["id"] for r in resp.data]
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            supabase.table(table).delete().in_("id", batch).execute()
        results[table]["deleted"] = len(ids)
        print(f"  DELETED {len(ids)} rows from {table}")
    except Exception as e:
        print(f"  ERROR deleting {table}: {e}")
else:
    print(f"  {table}: nothing to delete")

# 3. Delete storage files
if storage_files:
    try:
        for i in range(0, len(storage_files), 50):
            batch = storage_files[i:i+50]
            supabase.storage.from_("contracts").remove(batch)
        print(f"  DELETED {len(storage_files)} files from storage bucket")
    except Exception as e:
        print(f"  ERROR deleting storage files: {e}")
else:
    print(f"  Storage: nothing to delete")

# 4. Delete contracts
table = "contracts"
if results.get(table, {}).get("before", 0) > 0 and not results[table].get("missing"):
    try:
        resp = supabase.table(table).select("id").execute()
        ids = [r["id"] for r in resp.data]
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            supabase.table(table).delete().in_("id", batch).execute()
        results[table]["deleted"] = len(ids)
        print(f"  DELETED {len(ids)} rows from {table}")
    except Exception as e:
        print(f"  ERROR deleting {table}: {e}")
else:
    print(f"  {table}: nothing to delete")

# 5. Delete projects
table = "projects"
if results.get(table, {}).get("before", 0) > 0 and not results[table].get("missing"):
    try:
        resp = supabase.table(table).select("id").execute()
        ids = [r["id"] for r in resp.data]
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            supabase.table(table).delete().in_("id", batch).execute()
        results[table]["deleted"] = len(ids)
        print(f"  DELETED {len(ids)} rows from {table}")
    except Exception as e:
        print(f"  ERROR deleting {table}: {e}")
else:
    print(f"  {table}: nothing to delete")

print(f"\n  user_profiles: PRESERVED ({results.get('user_profiles', {}).get('before', 0)} rows kept)")

# --- Verify ---
print()
print("=" * 60)
print("PHASE 3: VERIFICATION — Confirming tables are empty")
print("=" * 60)

for table in ["red_flags", "analyses", "contracts", "projects"]:
    if results.get(table, {}).get("missing"):
        print(f"  {table:20s} → (table does not exist)")
        continue
    try:
        resp = supabase.table(table).select("id").execute()
        count = len(resp.data) if resp.data else 0
        status_str = "CLEAN" if count == 0 else f"WARNING: {count} rows remain!"
        print(f"  {table:20s} → {status_str}")
    except Exception as e:
        print(f"  {table:20s} → ERROR: {e}")

# Verify user_profiles still intact
try:
    resp = supabase.table("user_profiles").select("id, full_name, role").execute()
    print(f"\n  user_profiles → {len(resp.data)} users preserved:")
    for p in resp.data:
        print(f"    - {p.get('full_name', 'Unknown'):30s} role={p.get('role', '?')}")
except Exception as e:
    print(f"  user_profiles → ERROR: {e}")

# Verify storage is empty
print()
try:
    listed = supabase.storage.from_("contracts").list()
    remaining = 0
    for item in (listed or []):
        if item.get("id") is None:
            inner = supabase.storage.from_("contracts").list(item["name"])
            remaining += len([f for f in (inner or []) if f.get("id") is not None])
        else:
            remaining += 1
    status_str = "CLEAN" if remaining == 0 else f"WARNING: {remaining} files remain!"
    print(f"  Storage bucket    → {status_str}")
except Exception as e:
    print(f"  Storage bucket    → ERROR: {e}")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
for table in ["red_flags", "analyses", "contracts", "projects"]:
    info = results.get(table, {})
    if info.get("missing"):
        print(f"  {table:20s} — does not exist (skipped)")
    else:
        print(f"  {table:20s} — {info.get('before', 0)} found → {info.get('deleted', 0)} deleted")
print(f"  {'storage files':20s} — {len(storage_files)} found → {len(storage_files)} deleted")
print(f"  {'user_profiles':20s} — {results.get('user_profiles', {}).get('before', 0)} preserved (NOT deleted)")
print()
print("Data wipe complete. All pages should now show empty state.")
