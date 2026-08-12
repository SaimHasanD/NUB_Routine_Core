import os
import shutil
import tempfile
import traceback
from typing import Dict, Any

from fastapi import APIRouter, File, UploadFile, HTTPException, Header, Depends
from pydantic import BaseModel

from .shared import supabase_client, logger
from .parser import parse_excel, build_faculty_map
from .parser.time_utils import normalize_to_24h
from openpyxl import load_workbook

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

class IngestResponse(BaseModel):
    status: str
    semester: str
    inserted: Dict[str, int]
    warnings: list[str]

@router.post("/excel", response_model=IngestResponse)
async def ingest_excel(
    file: UploadFile = File(...),
    x_upload_password: str = Header(None, alias="X-Upload-Password")
):
    upload_pwd = os.environ.get("UPLOAD_PASSWORD", "admin123_nu")
    if not x_upload_password or x_upload_password != upload_pwd:
        raise HTTPException(status_code=401, detail="Missing or invalid upload password")

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        wb = load_workbook(tmp_path, data_only=True)
        faculty_map = build_faculty_map(wb)
        wb.close()
        
        parsed_data = await parse_excel(tmp_path)
    except Exception as exc:
        os.unlink(tmp_path)
        logger.error(f"Failed to parse excel: {traceback.format_exc()}")
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {exc}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    warnings = []

    # 1. Fetch departments
    dept_resp = supabase_client.table("departments").select("id, code").execute()
    dept_map = {d["code"]: d["id"] for d in dept_resp.data}
    ecse_dept_id = dept_map.get("ECSE")
    if not ecse_dept_id:
        raise HTTPException(status_code=500, detail="ECSE department not found in DB")

    # Fetch active semester for ECSE
    semesters_resp = supabase_client.table("semesters").select("id, name").eq("department_id", ecse_dept_id).eq("is_active", True).execute()
    if not semesters_resp.data:
        raise HTTPException(status_code=409, detail="No active semester found for ECSE — upload aborted")
    
    active_semester = semesters_resp.data[0]
    semester_id = active_semester["id"]
    semester_name = active_semester["name"]

    # --- DB Writes ---

    # 1. Teachers
    teachers_data = []
    for acro, info in faculty_map.items():
        if not acro:
            continue
        dept_id = dept_map.get(info.get("department"))
        teachers_data.append({
            "acronym": acro,
            "name": info.get("name"),
            "designation": info.get("designation"),
            "home_department_id": dept_id,
            "mobile_number": info.get("mobile"),
            "email": info.get("email"),
            "is_adjunct": False
        })
    if teachers_data:
        supabase_client.table("teachers").upsert(teachers_data, on_conflict="acronym").execute()

    # Re-fetch teachers for mapping
    teachers_resp = supabase_client.table("teachers").select("id, acronym").execute()
    teacher_id_map = {t["acronym"]: t["id"] for t in teachers_resp.data}

    # 2. Rooms
    rooms_data = []
    seen_rooms = set()
    for entries in parsed_data["index"].values():
        for e in entries:
            room_code = e.get("room")
            if not room_code or room_code.lower() == "online":
                continue
            if room_code in seen_rooms:
                continue
            seen_rooms.add(room_code)
            
            building = None
            if "(" in room_code and ")" in room_code:
                building = room_code.split("(")[1].split(")")[0]
                
            is_lab = e.get("section_type", "").startswith("lab")
            
            rooms_data.append({
                "room_code": room_code,
                "building": building,
                "is_lab": is_lab
            })
    if rooms_data:
        supabase_client.table("rooms").upsert(rooms_data, on_conflict="room_code").execute()

    # Re-fetch rooms for mapping
    rooms_resp = supabase_client.table("rooms").select("id, room_code").execute()
    room_id_map = {r["room_code"]: r["id"] for r in rooms_resp.data}

    # 3. Courses
    courses_data = []
    seen_courses = set()
    for entries in parsed_data["index"].values():
        for e in entries:
            course_code = e.get("course")
            if not course_code:
                continue
            course_code = course_code.upper().strip()
            if course_code in seen_courses:
                continue
            seen_courses.add(course_code)
            courses_data.append({
                "course_code": course_code
            })
    if courses_data:
        supabase_client.table("courses").upsert(courses_data, on_conflict="course_code").execute()

    # Re-fetch courses for mapping
    courses_resp = supabase_client.table("courses").select("id, course_code").execute()
    course_id_map = {c["course_code"]: c["id"] for c in courses_resp.data}

    # 4. Groups
    groups_data = []
    seen_groups = set()
    for g in parsed_data["groups"]:
        if g in seen_groups: continue
        seen_groups.add(g)
        
        academic_semester = int(g[0]) if g and g[0].isdigit() else None
        groups_data.append({
            "department_id": ecse_dept_id,
            "group_code": g,
            "academic_semester": academic_semester
        })
    if groups_data:
        supabase_client.table("groups").upsert(groups_data, on_conflict="department_id,group_code").execute()

    # Re-fetch groups for mapping
    groups_resp = supabase_client.table("groups").select("id, department_id, group_code").eq("department_id", ecse_dept_id).execute()
    group_id_map = {g["group_code"]: g["id"] for g in groups_resp.data}

    # Fetch time_slots
    ts_resp = supabase_client.table("time_slots").select("id, start_time").eq("semester_id", semester_id).execute()
    ts_map = {}
    for ts in ts_resp.data:
        # start_time is likely "08:00:00" in db
        st_db = ts["start_time"]
        if st_db.count(":") == 2:
            # Drop seconds
            st_db = ":".join(st_db.split(":")[:2])
        ts_map[st_db] = ts["id"]

    # 5. Class Routines
    # Delete existing
    supabase_client.table("class_routines").delete().eq("semester_id", semester_id).eq("department_id", ecse_dept_id).execute()

    cr_data = []
    skipped_ts_count = 0
    missing_acro_count = 0
    missing_room_count = 0

    for entries in parsed_data["index"].values():
        for e in entries:
            g_code = e.get("group")
            group_id = group_id_map.get(g_code)
            if not group_id:
                continue
                
            c_code = e.get("course")
            if c_code: c_code = c_code.upper().strip()
            course_id = course_id_map.get(c_code)
            if not course_id:
                continue

            # Teacher
            acro = e.get("teacher_acro")
            teacher_id = None
            if acro:
                teacher_id = teacher_id_map.get(acro)
                if not teacher_id:
                    missing_acro_count += 1
            
            # Room
            r_code = e.get("room")
            room_id = None
            if r_code and r_code.lower() != "online":
                room_id = room_id_map.get(r_code)
                if not room_id:
                    missing_room_count += 1

            # Time slot
            st_str = e.get("start_time")
            st_24h = normalize_to_24h(st_str)
            time_slot_id = ts_map.get(st_24h)
            
            if not time_slot_id:
                skipped_ts_count += 1
                continue

            day = e.get("day", "").lower()
            week_parity = e.get("odd_even")  # "odd" | "even" | None
            
            cr_data.append({
                "semester_id": semester_id,
                "department_id": ecse_dept_id,
                "group_id": group_id,
                "course_id": course_id,
                "teacher_id": teacher_id,
                "room_id": room_id,
                "time_slot_id": time_slot_id,
                "day_of_week": day,
                "week_parity": week_parity
            })

    # Insert routines in chunks of 500 to avoid too large payload
    inserted_routines = 0
    chunk_size = 500
    for i in range(0, len(cr_data), chunk_size):
        chunk = cr_data[i:i+chunk_size]
        res = supabase_client.table("class_routines").insert(chunk).execute()
        inserted_routines += len(chunk)

    if missing_acro_count > 0:
        warnings.append(f"Teacher acronyms not found in faculty sheet — teacher_id set to null for {missing_acro_count} entries")
    if missing_room_count > 0:
        warnings.append(f"Room empty or not found — room_id set to null for {missing_room_count} entries")
    if skipped_ts_count > 0:
        warnings.append(f"Time slots not matched in DB — {skipped_ts_count} entries skipped")

    for w in warnings:
        logger.warning(w)

    return IngestResponse(
        status="success",
        semester=semester_name,
        inserted={
            "teachers": len(teachers_data),
            "rooms": len(rooms_data),
            "courses": len(courses_data),
            "groups": len(groups_data),
            "class_routines": inserted_routines
        },
        warnings=warnings
    )
