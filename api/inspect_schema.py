"""
Inspect existing Supabase database schema
"""
import os
from dotenv import load_dotenv
from services.supabase import get_supabase_client

load_dotenv()

def inspect_schema():
    client = get_supabase_client()

    # Try to query each known table
    known_tables = ['user_profiles', 'projects', 'contracts', 'red_flags']

    for table in known_tables:
        print(f"\n{'='*60}")
        print(f"Table: {table}")
        print('='*60)
        try:
            # Get sample data to see structure
            all_data = client.table(table).select("*").limit(3).execute()

            if all_data.data and len(all_data.data) > 0:
                # Print columns
                columns = list(all_data.data[0].keys())
                print(f"\nColumns ({len(columns)}):")
                for col in columns:
                    sample_value = all_data.data[0][col]
                    value_type = type(sample_value).__name__
                    print(f"  - {col:30s} ({value_type})")

                print(f"\nSample rows ({len(all_data.data)}):")
                for i, row in enumerate(all_data.data, 1):
                    print(f"\n  Row {i}:")
                    for key, value in row.items():
                        # Truncate long values
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        print(f"    {key:30s} = {value}")
            else:
                print("  (empty table - checking with count)")
                count = client.table(table).select("*", count='exact').execute()
                print(f"  Total rows: {count.count}")

        except Exception as e:
            print(f"  Error: {e}")
            print(f"  Table might not exist or no access")

if __name__ == "__main__":
    inspect_schema()
