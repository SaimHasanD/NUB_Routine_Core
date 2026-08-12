import requests
import json
import os
from dotenv import load_dotenv
from supabase import create_client

# Load env to get supabase credentials
load_dotenv(".env")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("--- Uploading file ---")
with open(r"e:\NUB_Routine_Core\ECSE Summer.xlsx", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/ingest/excel",
        headers={"X-Upload-Password": "admin123"},
        files={"file": ("ECSE_Summer.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )

print(f"Status Code: {response.status_code}")
try:
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print("Response text:", response.text)

print("\n--- Verifying in Supabase ---")
def count_table(table_name):
    res = supabase.table(table_name).select("*", count="exact").limit(1).execute()
    return res.count

tables = ["teachers", "rooms", "courses", "groups", "class_routines"]
for t in tables:
    try:
        c = count_table(t)
        print(f"{t}: {c}")
    except Exception as e:
        print(f"{t}: error {e}")

print("\n--- Spot-check group 1A ---")
try:
    # Get group 1A id
    groups_res = supabase.table("groups").select("id").eq("group_code", "1A").execute()
    if not groups_res.data:
        print("Group 1A not found")
    else:
        group_id = groups_res.data[0]["id"]
        
        # Get routines
        res = supabase.table("class_routines").select(
            "day_of_week, week_parity, courses(course_code), teachers(acronym), rooms(room_code), time_slots(start_time)"
        ).eq("group_id", group_id).execute()
        
        # Sort and print
        entries = res.data
        def sort_key(e):
            day_order = {"sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4, "friday": 5, "saturday": 6}
            day = e.get("day_of_week") or "sunday"
            st = e.get("time_slots", {}).get("start_time") or "00:00:00"
            return (day_order.get(day.lower(), 99), st)
            
        entries.sort(key=sort_key)
        for e in entries:
            c = e.get("courses", {}) or {}
            t = e.get("teachers", {}) or {}
            r = e.get("rooms", {}) or {}
            ts = e.get("time_slots", {}) or {}
            
            print(f"1A | {c.get('course_code')} | {t.get('acronym')} | {r.get('room_code')} | {ts.get('start_time')} | {e.get('day_of_week')} | {e.get('week_parity')}")
except Exception as e:
    print("Spot-check error:", e)
