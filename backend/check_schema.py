import os
import sys
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("No supabase credentials")
    sys.exit(1)

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

tables = ["teachers", "rooms", "courses", "groups", "class_routines", "departments", "semesters", "time_slots", "online_classes"]

try:
    for table in tables:
        print(f"--- {table} ---")
        try:
            res = supabase.table(table).select("*").limit(1).execute()
            if hasattr(res, 'data'):
                if len(res.data) > 0:
                    print("Columns:", list(res.data[0].keys()))
                else:
                    print("Empty table, can't infer schema via select")
        except Exception as e:
            print(f"Error querying {table}: {e}")
except Exception as e:
    print(f"Global error: {e}")
