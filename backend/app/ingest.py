import os
import shutil
import tempfile
import traceback
from typing import Dict, Any

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import BaseModel

from .shared import supabase_client, logger
from .parser import parse_excel, build_faculty_map
from .parser.time_utils import normalize_to_24h
from openpyxl import load_workbook

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

class IngestResponse(BaseModel):
    status: str
    inserted: Dict[str, int]
    warnings: list[str]

@router.post("/excel", response_model=IngestResponse)
async def ingest_excel(
    department_code: str = Form(...),
    semester_id: str = Form(...),
    file: UploadFile = File(...)
):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    # Check department
    dept_resp = supabase_client.table("departments").select("id, code").eq("code", department_code).execute()
    if not dept_resp.data:
        raise HTTPException(status_code=400, detail=f"Department code '{department_code}' not found in DB")
    department_id = dept_resp.data[0]["id"]

    # Check semester
    sem_resp = supabase_client.table("semesters").select("id").eq("id", semester_id).execute()
    if not sem_resp.data:
        raise HTTPException(status_code=400, detail=f"Semester ID '{semester_id}' not found in DB")

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

    # 0. Validate sheet 1
    valid_entries = sum(len(entries) for entries in parsed_data["index"].values())
    if valid_entries == 0:
        raise HTTPException(status_code=500, detail="Entire Sheet 1 parse produces zero valid entries")

    warnings = []
    
    # 1. Teachers
    teachers_data = []
    for acro, info in faculty_map.items():
        if not acro:
            continue
        teachers_data.append({
            "name": info.get("name"),
            "acronym": acro,
            "designation": info.get("designation"),
            "mobile_number": info.get("mobile"),
            "email": info.get("email")
        })
    if teachers_data:
        supabase_client.table("teachers").upsert(teachers_data, on_conflict="acronym").execute()

    # Re-fetch for FKs
    teachers_resp = supabase_client.table("teachers").select("id, acronym").execute()
    teacher_map = {t["acronym"]: t["id"] for t in teachers_resp.data}

    # 2. Rooms
    rooms_data = []
    seen_rooms = set()
    for entries in parsed_data["index"].values():
        for e in entries:
            room_name = e.get("room")
            if not room_name or room_name.lower() == "online":
                continue
            if room_name in seen_rooms:
                continue
            seen_rooms.add(room_name)
            rooms_data.append({
                "room_code": room_name,
                "is_lab": "lab" in room_name.lower()
            })
    if rooms_data:
        supabase_client.table("rooms").upsert(rooms_data, on_conflict="room_code").execute()

    rooms_resp = supabase_client.table("rooms").select("id, room_code").execute()
    room_map = {r["room_code"]: r["id"] for r in rooms_resp.data}

    # 3. Courses
    courses_data = []
    seen_courses = set()
    for entries in parsed_data["index"].values():
        for e in entries:
            course = e.get("course")
            if not course:
                continue
            course_code = course.upper().strip()
            if course_code in seen_courses:
                continue
            seen_courses.add(course_code)
            courses_data.append({
                "course_code": course_code,
                "department_id": department_id
            })
    if courses_data:
        supabase_client.table("courses").upsert(courses_data, on_conflict="course_code").execute()

    courses_resp = supabase_client.table("courses").select("id, course_code").execute()
    course_map = {c["course_code"]: c["id"] for c in courses_resp.data}

    # 4. Groups
    groups_data = []
    seen_groups = set()
    for entries in parsed_data["index"].values():
        for e in entries:
            group_code = e.get("group")
            if not group_code or group_code in seen_groups:
                continue
            seen_groups.add(group_code)
            try:
                academic_semester = int(group_code[0])
            except (ValueError, IndexError):
                academic_semester = 1 # fallback
            groups_data.append({
                "department_id": department_id,
                "group_code": group_code,
                "academic_semester": academic_semester
            })
    if groups_data:
        supabase_client.table("groups").upsert(groups_data, on_conflict="department_id,group_code").execute()

    groups_resp = supabase_client.table("groups").select("id, group_code").eq("department_id", department_id).execute()
    group_map = {g["group_code"]: g["id"] for g in groups_resp.data}

    # 5. Class Routines
    ts_resp = supabase_client.table("time_slots").select("id, start_time").eq("semester_id", semester_id).execute()
    ts_map = {}
    for ts in ts_resp.data:
        st_db = ts["start_time"]
        if st_db.count(":") == 2:
            st_db = ":".join(st_db.split(":")[:2])
        ts_map[st_db] = ts["id"]

    cr_data = []
    oc_data = []
    for row_idx, (room_str, entries) in enumerate(parsed_data["index"].items()):
        for col_idx, e in enumerate(entries):
            course_code = e.get("course")
            if course_code: course_code = course_code.upper().strip()
            course_id = course_map.get(course_code)
            
            group_code = e.get("group")
            group_id = group_map.get(group_code)
            
            teacher_acro = e.get("teacher_acro")
            teacher_id = teacher_map.get(teacher_acro)
            
            room_name = e.get("room")
            room_id = room_map.get(room_name)
            
            day = e.get("day", "").lower()
            st_str = e.get("start_time")
            st_24h = normalize_to_24h(st_str)
            time_slot_id = ts_map.get(st_24h)
            
            is_online = (room_name and room_name.lower() == "online") or "online" in e.get("section_type", "").lower()
            
            if is_online:
                end_str = e.get("end_time")
                end_24h = normalize_to_24h(end_str) if end_str else None
                if st_24h and st_24h.count(":") == 1: st_24h += ":00"
                if end_24h and end_24h.count(":") == 1: end_24h += ":00"
                
                failed = []
                if not course_id: failed.append(f"course '{course_code}'")
                if not group_id: failed.append(f"group '{group_code}'")
                if not teacher_id and teacher_acro: failed.append(f"teacher acronym '{teacher_acro}'")
                
                if failed:
                    warnings.append(f"Could not resolve {', '.join(failed)} for online class '{course_code}-{group_code}'")
                    continue
                    
                oc_data.append({
                    "semester_id": semester_id,
                    "department_id": department_id,
                    "group_id": group_id,
                    "course_id": course_id,
                    "teacher_id": teacher_id,
                    "day_of_week": day,
                    "time_start": st_24h,
                    "time_end": end_24h
                })
            else:
                failed = []
                if not course_id: failed.append(f"course '{course_code}'")
                if not group_id: failed.append(f"group '{group_code}'")
                if not teacher_id and teacher_acro: failed.append(f"teacher acronym '{teacher_acro}'")
                if not room_id: failed.append(f"room '{room_name}'")
                if not time_slot_id: failed.append(f"time slot '{st_str}'")
    
                if failed:
                    warnings.append(f"Could not resolve {', '.join(failed)} for entry '{course_code}-{group_code}' at room '{room_name}', slot '{st_str}'")
                    continue
    
                week_parity = e.get("odd_even")
                if week_parity:
                    week_parity = week_parity.lower()
                    if week_parity not in ["odd", "even"]:
                        week_parity = None
                
                cr_data.append({
                    "semester_id": semester_id,
                    "department_id": department_id,
                    "group_id": group_id,
                    "course_id": course_id,
                    "teacher_id": teacher_id,
                    "room_id": room_id,
                    "time_slot_id": time_slot_id,
                    "day_of_week": day,
                    "week_parity": week_parity
                })

    cr_inserted = 0
    if cr_data:
        chunk_size = 500
        for i in range(0, len(cr_data), chunk_size):
            chunk = cr_data[i:i+chunk_size]
            res = supabase_client.table("class_routines").insert(chunk).execute()
            if hasattr(res, 'data') and res.data:
                cr_inserted += len(res.data)
            else:
                cr_inserted += len(chunk)

    oc_inserted = 0
    if oc_data:
        chunk_size = 500
        for i in range(0, len(oc_data), chunk_size):
            chunk = oc_data[i:i+chunk_size]
            res = supabase_client.table("online_classes").insert(chunk).execute()
            if hasattr(res, 'data') and res.data:
                oc_inserted += len(res.data)
            else:
                oc_inserted += len(chunk)

    for w in warnings:
        logger.warning(w)

    return IngestResponse(
        status="ok",
        inserted={
            "teachers": len(teachers_data),
            "rooms": len(rooms_data),
            "courses": len(courses_data),
            "groups": len(groups_data),
            "class_routines": cr_inserted,
            "online_classes": oc_inserted
        },
        warnings=warnings
    )
