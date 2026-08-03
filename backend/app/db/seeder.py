import re
from datetime import date, datetime, time
from sqlalchemy.orm import Session
from .models import (
    Department, Semester, Group, Teacher, Room, TimeSlot, Course, ClassRoutine, OnlineClass
)

def _parse_time(time_str: str) -> time:
    """Helper to safely parse time strings like '10:30 am' or '02:00 PM' to time objects."""
    import re
    time_str = str(time_str).strip().lower()
    match = re.match(r"(\d{1,2}):?(\d{2})?\s*(am|pm)?", time_str)
    if not match:
        return time(0, 0)
    
    hr_str = match.group(1)
    min_str = match.group(2) or "00"
    meridiem = match.group(3)

    hr = int(hr_str)
    mn = int(min_str)
    
    if meridiem == "pm" and hr < 12:
        hr += 12
    elif meridiem == "am" and hr == 12:
        hr = 0
        
    return time(hr, mn)

def seed_from_upload(data: dict, db: Session, replace: bool = False):
    # 1. Department
    dept = db.query(Department).filter(Department.code == "ECSE").first()
    if not dept:
        dept = Department(code="ECSE", name="Electrical and Computer Science Engineering")
        db.add(dept)
        db.flush()

    # 2. Semester
    season = data.get("season") or "Unknown"
    semester = db.query(Semester).filter(
        Semester.department_id == dept.id,
        Semester.name == season
    ).first()
    
    if not semester:
        semester = Semester(
            department_id=dept.id,
            name=season,
            start_date=date.today(), 
            is_active=True
        )
        db.add(semester)
        db.flush()
        
    # If replace, clear out old routines for this semester
    if replace:
        db.query(ClassRoutine).filter(ClassRoutine.semester_id == semester.id).delete()
        db.query(OnlineClass).filter(OnlineClass.semester_id == semester.id).delete()
        db.flush()

    index = data.get("index", {})
    
    # 3. Setup Caches to prevent massive DB calls
    course_cache = {}
    teacher_cache = {}
    room_cache = {}
    group_cache = {}
    timeslot_cache = {}
    
    slot_order_counter = 1

    for group_name, entries in index.items():
        # Get/Create Group
        if group_name not in group_cache:
            g = db.query(Group).filter(
                Group.department_id == dept.id, 
                Group.group_code == group_name
            ).first()
            if not g:
                # Naive semester extraction (e.g., '1A' -> 1)
                ac_sem_match = re.search(r"^(\d+)", group_name)
                ac_sem = int(ac_sem_match.group(1)) if ac_sem_match else 1
                g = Group(department_id=dept.id, group_code=group_name, academic_semester=ac_sem)
                db.add(g)
                db.flush()
            group_cache[group_name] = g
            
        group_obj = group_cache[group_name]

        for e in entries:
            # Get/Create Teacher
            t_acro = e.get("teacher_acro", "").strip() or "TBA"
            if t_acro not in teacher_cache:
                t = db.query(Teacher).filter(Teacher.acronym == t_acro).first()
                if not t:
                    t_info = e.get("teacher") or {}
                    t_name = t_info.get("name", t_acro) if isinstance(t_info, dict) else str(t_info)
                    t = Teacher(
                        acronym=t_acro,
                        name=t_name,
                        designation=t_info.get("designation") if isinstance(t_info, dict) else None,
                        mobile_number=t_info.get("mobile") if isinstance(t_info, dict) else None,
                        email=t_info.get("email") if isinstance(t_info, dict) else None,
                    )
                    db.add(t)
                    db.flush()
                teacher_cache[t_acro] = t
            teacher_obj = teacher_cache[t_acro]
            
            # Get/Create Course
            c_code = e.get("course_code", "").strip()
            if c_code not in course_cache:
                c = db.query(Course).filter(Course.course_code == c_code).first()
                if not c:
                    c = Course(course_code=c_code, department_id=dept.id)
                    db.add(c)
                    db.flush()
                course_cache[c_code] = c
            course_obj = course_cache[c_code]

            # Get/Create Room
            r_code = e.get("room", "").strip() or "TBA"
            if r_code not in room_cache:
                r = db.query(Room).filter(Room.room_code == r_code).first()
                if not r:
                    is_lab = "lab" in str(r_code).lower()
                    r = Room(room_code=r_code, is_lab=is_lab)
                    db.add(r)
                    db.flush()
                room_cache[r_code] = r
            room_obj = room_cache[r_code]

            # Parse Times
            t_start = _parse_time(e.get("start_time", ""))
            t_end = _parse_time(e.get("end_time", ""))
            
            is_online = "online" in e.get("section_type", "").lower()
            
            if is_online:
                oc = OnlineClass(
                    semester_id=semester.id,
                    department_id=dept.id,
                    group_id=group_obj.id,
                    course_id=course_obj.id,
                    teacher_id=teacher_obj.id,
                    day_of_week=e.get("day", ""),
                    time_start=t_start,
                    time_end=t_end
                )
                db.add(oc)
            else:
                # Get/Create TimeSlot
                time_key = f"{t_start}-{t_end}"
                if time_key not in timeslot_cache:
                    ts = db.query(TimeSlot).filter(
                        TimeSlot.semester_id == semester.id,
                        TimeSlot.start_time == t_start,
                        TimeSlot.end_time == t_end
                    ).first()
                    if not ts:
                        ts = TimeSlot(
                            semester_id=semester.id,
                            start_time=t_start,
                            end_time=t_end,
                            slot_order=slot_order_counter
                        )
                        db.add(ts)
                        db.flush()
                        slot_order_counter += 1
                    timeslot_cache[time_key] = ts
                timeslot_obj = timeslot_cache[time_key]
                
                cr = ClassRoutine(
                    semester_id=semester.id,
                    department_id=dept.id,
                    group_id=group_obj.id,
                    course_id=course_obj.id,
                    teacher_id=teacher_obj.id,
                    room_id=room_obj.id,
                    time_slot_id=timeslot_obj.id,
                    day_of_week=e.get("day", ""),
                    week_parity=e.get("odd_even", None)
                )
                db.add(cr)

    db.commit()
    return semester.id
