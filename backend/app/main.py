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
    
    if not routines:
        return []

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
        teachers = supabase_client.table("teachers").select("id, name").in_("id", teacher_ids).execute().data
        teachers_dict = {t["id"]: t for t in teachers}
        
    rooms_dict = {}
    if room_ids:
        rooms = supabase_client.table("rooms").select("id, room_code").in_("id", room_ids).execute().data
        rooms_dict = {r["id"]: r for r in rooms}
        
    time_slots_dict = {}
    if time_slot_ids:
        time_slots = supabase_client.table("time_slots").select("id, start_time, end_time").in_("id", time_slot_ids).execute().data
        time_slots_dict = {ts["id"]: ts for ts in time_slots}
        
    result = []
    for r in routines:
        course = courses_dict.get(r.get("course_id"))
        teacher = teachers_dict.get(r.get("teacher_id"))
        room = rooms_dict.get(r.get("room_id"))
        time_slot = time_slots_dict.get(r.get("time_slot_id"))
        
        result.append({
            "id": r["id"],
            "day": r["day_of_week"].capitalize() if r.get("day_of_week") else None,
            "course": course["course_code"] if course else None,
            "teacher": teacher["name"] if teacher else None,
            "room": room["room_code"] if room else None,
            "start_time": time_slot["start_time"] if time_slot else None,
            "end_time": time_slot["end_time"] if time_slot else None,
            "odd_even": r.get("week_parity"),
            "section_type": "Lab" if r.get("week_parity") is not None else "Theory"
        })
        
    return result
