import os
import shutil
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


# Local imports
try:
    from .models import UploadResponse, GroupRoutineResponse, ScheduleEntry as SchemaScheduleEntry
except ImportError:
    from models import UploadResponse, GroupRoutineResponse, ScheduleEntry as SchemaScheduleEntry

try:
    from . import parse_excel
except ImportError:
    from __init__ import parse_excel

try:
    from .shared import ADMIN_PASSWORD, SUPABASE_BUCKET, supabase_client, DATA_DIR, logger
except ImportError:
    from shared import ADMIN_PASSWORD, SUPABASE_BUCKET, supabase_client, DATA_DIR, logger

try:
    from .exam import router as exam_router
except ImportError:
    from exam import router as exam_router

try:
    from .parser.time_utils import normalize_to_24h, merge_consecutive_entries
except ImportError:
    from parser.time_utils import normalize_to_24h, merge_consecutive_entries

try:
    from .ingest import router as ingest_router
except ImportError:
    from ingest import router as ingest_router



def _resolve_source_file() -> Path | None:
    files = sorted(DATA_DIR.glob("*.xlsx"))
    if files:
        return files[0]
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    if supabase_client:
        try:
            files = supabase_client.storage.from_(SUPABASE_BUCKET).list()
            excel_files = [f for f in files if isinstance(f, dict) and f.get('name', '').endswith('.xlsx')]
            if excel_files:
                excel_files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                latest_filename = excel_files[0]['name']
                file_bytes = supabase_client.storage.from_(SUPABASE_BUCKET).download(latest_filename)

                for old_file in DATA_DIR.glob("*.xlsx"):
                    old_file.unlink()

                dest_path = DATA_DIR / latest_filename
                with open(dest_path, "wb") as f:
                    f.write(file_bytes)
                logger.info(f"Synced latest routine file '{latest_filename}' for downloads.")
        except Exception as e:
            logger.warning(f"Failed to sync from Supabase: {e}")
    yield

app = FastAPI(title="ECSE Routine Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exam_router)
app.include_router(ingest_router)

# ── Health ────────────────────────────────────────────────────────────────────
@app.api_route("/api/v1/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}

# ── Admin Status ──────────────────────────────────────────────────────────────
@app.get("/api/v1/admin/status")
async def admin_status():
    if not supabase_client:
        return {
            "loaded": False,
            "filename": None,
            "uploaded_at": None,
            "groups_count": 0,
            "total_entries": 0,
        }
    
    sem_res = supabase_client.table("semesters").select("*").order("created_at", desc=True).limit(1).execute()
    if not sem_res.data:
        return {
            "loaded": False,
            "filename": None,
            "uploaded_at": None,
            "groups_count": 0,
            "total_entries": 0,
        }
    
    semester = sem_res.data[0]
    
    # We do a normal select since postgrest count is slightly complex with supabase-py
    # and the dataset is extremely small (400 rows).
    groups_res = supabase_client.table("groups").select("id").eq("department_id", semester["department_id"]).execute()
    cr_res = supabase_client.table("class_routines").select("id").eq("semester_id", semester["id"]).execute()
    oc_res = supabase_client.table("online_classes").select("id").eq("semester_id", semester["id"]).execute()

    source = _resolve_source_file()

    return {
        "loaded": True,
        "filename": source.name if source else "Routine Excel File",
        "uploaded_at": semester["created_at"],
        "groups_count": len(groups_res.data) if groups_res.data else 0,
        "total_entries": (len(cr_res.data) if cr_res.data else 0) + (len(oc_res.data) if oc_res.data else 0),
    }

# ── Upload ────────────────────────────────────────────────────────────────────
@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), password: str = Form(""), replace: bool = Form(False)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid admin password.")

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        data = await parse_excel(tmp_path)
    except Exception as exc:
        os.unlink(tmp_path)
        raise HTTPException(422, f"Failed to parse file: {exc}")

    for old_file in DATA_DIR.glob("*.xlsx"):
        old_file.unlink()

    dest = DATA_DIR / file.filename
    shutil.move(tmp_path, str(dest))

    if supabase_client:
        try:
            files = supabase_client.storage.from_(SUPABASE_BUCKET).list()
            old_files = [f['name'] for f in files if isinstance(f, dict) and f.get('name', '').endswith('.xlsx')]
            if old_files:
                supabase_client.storage.from_(SUPABASE_BUCKET).remove(old_files)

            with open(dest, "rb") as f:
                file_bytes = f.read()
            supabase_client.storage.from_(SUPABASE_BUCKET).upload(
                file.filename,
                file_bytes,
                file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
            )
        except Exception as e:
            logger.warning(f"Failed to sync with Supabase: {e}")



    action = "Replaced" if replace else "Uploaded"
    return UploadResponse(
        groups=data["groups"],
        total_entries=data["total"],
        title=data.get("title"),
        season=data.get("season"),
        odd_week_dates=data.get("odd_week_dates", []),
        even_week_dates=data.get("even_week_dates", []),
        message=f"{action} successfully. {data['total']} entries across {len(data['groups'])} groups."
    )

# ── Groups ────────────────────────────────────────────────────────────────────
@app.get("/api/v1/groups")
async def list_groups():
    return supabase_client.table("groups").select("*").execute().data

@app.get("/api/v1/source-file")
async def download_source_file():
    source_path = _resolve_source_file()
    if source_path is None:
        raise HTTPException(404, "Source file not found on disk.")

    return FileResponse(
        path=str(source_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=source_path.name,
    )

# ── Routine by group ──────────────────────────────────────────────────────────
@app.get("/api/v1/routine/{group_id}")
async def get_routine(group_id: str):
    routines = supabase_client.table("class_routines").select("*").eq("group_id", group_id).execute().data
    
    group_res = supabase_client.table("groups").select("department_id").eq("id", group_id).execute()
    if not group_res.data:
        raise HTTPException(404, "Group not found")
    department_id = group_res.data[0]["department_id"]
    
    semester_res = supabase_client.table("semesters").select("id, name, start_date").eq("department_id", department_id).eq("is_active", True).execute()
    if not semester_res.data:
        semester_obj = {"name": "Unknown", "start_date": None}
        odd_dates, even_dates = [], []
    else:
        sem_data = semester_res.data[0]
        semester_obj = {"name": sem_data["name"], "start_date": sem_data["start_date"]}
        
        weeks = supabase_client.table("semester_weeks").select("week_number, week_start_date, parity").eq("semester_id", sem_data["id"]).order("week_number").execute().data
        odd_dates = []
        even_dates = []
        if weeks:
            for w in weeks:
                sd = w.get("week_start_date")
                formatted = sd
                if sd and "-" in sd:
                    parts = sd.split("-")
                    if len(parts) >= 3:
                        formatted = f"{parts[2][:2]}.{parts[1]}.{parts[0]}"
                
                if w.get("parity") == "odd":
                    odd_dates.append(formatted)
                elif w.get("parity") == "even":
                    even_dates.append(formatted)

    if not routines:
        return {
            "semester": semester_obj,
            "odd_week_dates": odd_dates,
            "even_week_dates": even_dates,
            "routine": []
        }

    course_ids = list({r["course_id"] for r in routines if r.get("course_id")})
    teacher_ids = list({r["teacher_id"] for r in routines if r.get("teacher_id")})
    room_ids = list({r["room_id"] for r in routines if r.get("room_id")})
    time_slot_ids = list({r["time_slot_id"] for r in routines if r.get("time_slot_id")})
    
    courses_dict = {}
    if course_ids:
        courses = supabase_client.table("courses").select("id, course_code").in_("id", course_ids).execute().data
        courses_dict = {c["id"]: c for c in courses}
        
    teachers_dict = {}
    if teacher_ids:
        teachers = supabase_client.table("teachers").select("id, acronym, name, designation, mobile_number, email, is_adjunct").in_("id", teacher_ids).execute().data
        for t in teachers:
            teachers_dict[t["id"]] = {
                "acronym": t.get("acronym"),
                "name": t.get("name"),
                "designation": t.get("designation"),
                "mobile": t.get("mobile_number"),
                "email": t.get("email"),
                "is_adjunct": t.get("is_adjunct")
            }
        
    rooms_dict = {}
    if room_ids:
        rooms = supabase_client.table("rooms").select("id, room_code").in_("id", room_ids).execute().data
        rooms_dict = {r["id"]: r for r in rooms}
        
    time_slots_dict = {}
    if time_slot_ids:
        time_slots = supabase_client.table("time_slots").select("id, start_time, end_time").in_("id", time_slot_ids).execute().data
        time_slots_dict = {ts["id"]: ts for ts in time_slots}

    theory_rows = []
    seen_theory_keys = set()
    lab_entries = {}
    
    for r in routines:
        key = (r.get("day_of_week"), r.get("course_id"), r.get("teacher_id"), r.get("room_id"), r.get("time_slot_id"))
        if r.get("week_parity") is None:
            if key not in seen_theory_keys:
                seen_theory_keys.add(key)
                theory_rows.append(r)
        else:
            if key not in lab_entries:
                lab_entries[key] = {"row": r, "parities": set()}
            lab_entries[key]["parities"].add(r.get("week_parity"))

    final_rows = []
    final_rows.extend(theory_rows)
    for key, data in lab_entries.items():
        row = data["row"].copy()
        parities = data["parities"]
        if "odd" in parities and "even" in parities:
            row["week_parity"] = "both"
        elif "odd" in parities:
            row["week_parity"] = "odd"
        elif "even" in parities:
            row["week_parity"] = "even"
        final_rows.append(row)
        
    result = []
    for r in final_rows:
        course = courses_dict.get(r.get("course_id"))
        teacher = teachers_dict.get(r.get("teacher_id"))
        room = rooms_dict.get(r.get("room_id"))
        time_slot = time_slots_dict.get(r.get("time_slot_id"))
        
        section_type = "Theory" if r.get("week_parity") is None else "Lab"
        
        result.append({
            "id": r["id"],
            "day": r["day_of_week"].capitalize() if r.get("day_of_week") else None,
            "course": course["course_code"] if course else None,
            "teacher": teacher if teacher else None,
            "room": room["room_code"] if room else None,
            "start_time": time_slot["start_time"] if time_slot else None,
            "end_time": time_slot["end_time"] if time_slot else None,
            "odd_even": r.get("week_parity"),
            "section_type": section_type
        })
        
    def get_group_key(r):
        t_acro = r["teacher"]["acronym"] if r["teacher"] else ""
        return (r["day"], r["course"], t_acro, r["room"], r["odd_even"], r["section_type"])

    result.sort(key=lambda x: (get_group_key(x), x["start_time"]))

    merged_result = []
    for r in result:
        if not merged_result:
            merged_result.append(r)
            continue
            
        last = merged_result[-1]
        if get_group_key(last) == get_group_key(r) and last["end_time"] == r["start_time"]:
            last["end_time"] = r["end_time"]
        else:
            merged_result.append(r)
            
    # Optional: re-sort by day (using some standard order) and start_time, or just leave it.
    # The frontend already groups by day. 
    # But to keep output clean, let's sort by day of week then start_time.
    days_order = {"Sunday": 1, "Monday": 2, "Tuesday": 3, "Wednesday": 4, "Thursday": 5, "Friday": 6, "Saturday": 7}
    merged_result.sort(key=lambda x: (days_order.get(x["day"], 99), x["start_time"]))
        
    return {
        "semester": semester_obj,
        "odd_week_dates": odd_dates,
        "even_week_dates": even_dates,
        "routine": merged_result
    }

# ── Teachers API ──────────────────────────────────────────────────────────────
@app.get("/api/v1/teachers")
async def get_teachers():
    teachers = supabase_client.table("teachers").select("id, acronym, name, designation, department, mobile_number, email").execute().data
    return teachers

@app.get("/api/v1/teachers/schedule")
async def get_teachers_schedule():
    routines = supabase_client.table("class_routines").select("*").execute().data
    if not routines:
        return []
        
    course_ids = list({r["course_id"] for r in routines if r.get("course_id")})
    teacher_ids = list({r["teacher_id"] for r in routines if r.get("teacher_id")})
    room_ids = list({r["room_id"] for r in routines if r.get("room_id")})
    time_slot_ids = list({r["time_slot_id"] for r in routines if r.get("time_slot_id")})
    group_ids = list({r["group_id"] for r in routines if r.get("group_id")})
    
    courses_dict = {c["id"]: c for c in supabase_client.table("courses").select("id, course_code, course_name").in_("id", course_ids).execute().data} if course_ids else {}
    teachers_dict = {t["id"]: t for t in supabase_client.table("teachers").select("id, acronym").in_("id", teacher_ids).execute().data} if teacher_ids else {}
    rooms_dict = {r["id"]: r for r in supabase_client.table("rooms").select("id, room_code").in_("id", room_ids).execute().data} if room_ids else {}
    time_slots_dict = {ts["id"]: ts for ts in supabase_client.table("time_slots").select("id, start_time, end_time").in_("id", time_slot_ids).execute().data} if time_slot_ids else {}
    groups_dict = {g["id"]: g for g in supabase_client.table("groups").select("id, group_code").in_("id", group_ids).execute().data} if group_ids else {}

    result = []
    for r in routines:
        course = courses_dict.get(r.get("course_id"))
        teacher = teachers_dict.get(r.get("teacher_id"))
        room = rooms_dict.get(r.get("room_id"))
        time_slot = time_slots_dict.get(r.get("time_slot_id"))
        group = groups_dict.get(r.get("group_id"))
        
        result.append({
            "course_code": course["course_code"] if course else None,
            "course": course["course_name"] if course and "course_name" in course else None,
            "group": group["group_code"] if group else None,
            "teacher_acro": teacher["acronym"] if teacher else None,
            "room": room["room_code"] if room else None,
            "start_time": time_slot["start_time"] if time_slot else None,
            "end_time": time_slot["end_time"] if time_slot else None,
            "day": r.get("day_of_week").capitalize() if r.get("day_of_week") else None,
            "type": "Theory" if r.get("week_parity") is None else "Lab"
        })
    return result
