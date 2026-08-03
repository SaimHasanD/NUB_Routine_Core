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
from sqlalchemy.orm import Session

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
    from .time_utils import normalize_to_24h, merge_consecutive_entries
except ImportError:
    from time_utils import normalize_to_24h, merge_consecutive_entries

try:
    from .db.database import engine, get_db, Base
except ImportError:
    from db.database import engine, get_db, Base

try:
    from .db.models import Department, Semester, Group, Teacher, Room, TimeSlot, Course, ClassRoutine, OnlineClass
except ImportError:
    from db.models import Department, Semester, Group, Teacher, Room, TimeSlot, Course, ClassRoutine, OnlineClass

try:
    from .db.seeder import seed_from_upload
except ImportError:
    from db.seeder import seed_from_upload

# Create tables
Base.metadata.create_all(bind=engine)

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

# ── Health ────────────────────────────────────────────────────────────────────
@app.api_route("/api/v1/health", methods=["GET", "HEAD"])
async def health(db: Session = Depends(get_db)):
    dept = db.query(Department).first()
    return {"status": "ok", "loaded": dept is not None}

# ── Admin Status ──────────────────────────────────────────────────────────────
@app.get("/api/v1/admin/status")
async def admin_status(db: Session = Depends(get_db)):
    semester = db.query(Semester).order_by(Semester.created_at.desc()).first()
    if not semester:
        return {
            "loaded": False,
            "filename": None,
            "uploaded_at": None,
            "groups_count": 0,
            "total_entries": 0,
        }
    
    groups_count = db.query(Group).filter(Group.department_id == semester.department_id).count()
    cr_count = db.query(ClassRoutine).filter(ClassRoutine.semester_id == semester.id).count()
    oc_count = db.query(OnlineClass).filter(OnlineClass.semester_id == semester.id).count()

    source = _resolve_source_file()

    return {
        "loaded": True,
        "filename": source.name if source else None,
        "uploaded_at": semester.created_at.isoformat() if semester.created_at else None,
        "groups_count": groups_count,
        "total_entries": cr_count + oc_count,
    }

# ── Upload ────────────────────────────────────────────────────────────────────
@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), password: str = Form(""), replace: bool = Form(False), db: Session = Depends(get_db)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid admin password.")

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx files are supported.")

    existing_cr = db.query(ClassRoutine).first()
    if existing_cr and not replace:
        raise HTTPException(409, "A routine is already loaded. Use replace to overwrite it.")

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

    try:
        seed_from_upload(data, db, replace)
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise HTTPException(500, f"Failed to store in DB: {e}")

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
async def list_groups(db: Session = Depends(get_db)):
    semester = db.query(Semester).order_by(Semester.created_at.desc()).first()
    if not semester:
        return {
            "groups": [],
            "title": None,
            "season": None,
            "source_filename": None,
            "source_available": False,
        }
    
    groups = db.query(Group).filter(Group.department_id == semester.department_id).order_by(Group.group_code).all()
    group_names = [g.group_code for g in groups]
    source_path = _resolve_source_file()
    
    return {
        "groups": group_names,
        "title": f"Routine for {semester.name}",
        "season": semester.name,
        "source_filename": source_path.name if source_path else None,
        "source_available": source_path is not None,
    }

@app.get("/api/v1/source-file")
async def download_source_file(db: Session = Depends(get_db)):
    source_path = _resolve_source_file()
    if source_path is None:
        raise HTTPException(404, "Source file not found on disk.")

    return FileResponse(
        path=str(source_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=source_path.name,
    )

# ── Routine by group ──────────────────────────────────────────────────────────
@app.get("/api/v1/routine/{group_id}", response_model=GroupRoutineResponse)
async def get_routine(group_id: str, db: Session = Depends(get_db)):
    group_id = group_id.upper()
    semester = db.query(Semester).order_by(Semester.created_at.desc()).first()
    if not semester:
        raise HTTPException(404, "No routine loaded. Please upload a file first.")

    group = db.query(Group).filter(
        Group.department_id == semester.department_id, 
        Group.group_code == group_id
    ).first()
    
    if not group:
        raise HTTPException(404, f"Group '{group_id}' not found.")

    cr_entries = db.query(ClassRoutine).filter(
        ClassRoutine.semester_id == semester.id,
        ClassRoutine.group_id == group.id
    ).all()
    
    oc_entries = db.query(OnlineClass).filter(
        OnlineClass.semester_id == semester.id,
        OnlineClass.group_id == group.id
    ).all()
    
    formatted_entries = []
    
    # Process Regular & Lab Routines
    for cr in cr_entries:
        c = db.query(Course).get(cr.course_id)
        t = db.query(Teacher).get(cr.teacher_id) if cr.teacher_id else None
        r = db.query(Room).get(cr.room_id) if cr.room_id else None
        ts = db.query(TimeSlot).get(cr.time_slot_id)
        
        t_dict = {
            "name": t.name if t else "",
            "designation": t.designation if t else "",
            "department": "", # Home dept joined not required for output payload
            "mobile": t.mobile_number if t else "",
            "email": t.email if t else ""
        }
        
        start_t = ts.start_time.strftime("%I:%M %p").lower() if ts else ""
        end_t = ts.end_time.strftime("%I:%M %p").lower() if ts else ""
        if start_t.startswith("0"): start_t = start_t[1:]
        if end_t.startswith("0"): end_t = end_t[1:]
        
        slot_str = f"{start_t}-{end_t}"

        sec_type = "lab" if (r and r.is_lab) else "theory"
        if cr.week_parity:
            sec_type = f"lab_{cr.week_parity}"
            
        formatted_entries.append({
            "course_code": c.course_code if c else "",
            "course": c.course_code if c else "",
            "group": group.group_code,
            "teacher_acro": t.acronym if t else "",
            "teacher": t_dict,
            "room": r.room_code if r else "",
            "time_slot": slot_str,
            "start_time": start_t,
            "end_time": end_t,
            "day": cr.day_of_week or "Sunday",
            "type": sec_type.split('_')[0],
            "odd_even": cr.week_parity,
            "section_type": sec_type,
            "week_note": ""
        })
        
    # Process Online Classes
    for oc in oc_entries:
        c = db.query(Course).get(oc.course_id)
        t = db.query(Teacher).get(oc.teacher_id) if oc.teacher_id else None
        
        t_dict = {
            "name": t.name if t else "",
            "designation": t.designation if t else "",
            "department": "",
            "mobile": t.mobile_number if t else "",
            "email": t.email if t else ""
        }
        
        start_t = oc.time_start.strftime("%I:%M %p").lower() if oc else ""
        end_t = oc.time_end.strftime("%I:%M %p").lower() if oc else ""
        if start_t.startswith("0"): start_t = start_t[1:]
        if end_t.startswith("0"): end_t = end_t[1:]
        
        slot_str = f"{start_t}-{end_t}"
            
        formatted_entries.append({
            "course_code": c.course_code if c else "",
            "course": c.course_code if c else "",
            "group": group.group_code,
            "teacher_acro": t.acronym if t else "",
            "teacher": t_dict,
            "room": "Online",
            "time_slot": slot_str,
            "start_time": start_t,
            "end_time": end_t,
            "day": oc.day_of_week or "Sunday",
            "type": "theory",
            "odd_even": None,
            "section_type": "online",
            "week_note": ""
        })

    merged = merge_consecutive_entries(formatted_entries)

    day_order = {"Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6}

    def sort_key(e):
        day_idx = day_order.get(e.get("day", "Sunday"), 99)
        start_24 = normalize_to_24h(e.get("start_time", ""))
        return (day_idx, start_24)

    merged.sort(key=sort_key)

    return GroupRoutineResponse(
        group=group_id,
        title=f"Routine for {semester.name}",
        season=semester.name,
        odd_week_dates=[],
        even_week_dates=[],
        entries=[SchemaScheduleEntry(**e) for e in merged]
    )
