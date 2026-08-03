import uuid
from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, Time, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID

class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    impl = CHAR
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))
            
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int
                
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

class Department(Base):
    __tablename__ = "departments"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DepartmentSource(Base):
    __tablename__ = "department_sources"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    department_id = Column(GUID(), ForeignKey("departments.id"))
    source_type = Column(String, nullable=False)
    sheet_url = Column(String, nullable=True)
    check_interval_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Semester(Base):
    __tablename__ = "semesters"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    department_id = Column(GUID(), ForeignKey("departments.id"))
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SemesterWeek(Base):
    __tablename__ = "semester_weeks"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    semester_id = Column(GUID(), ForeignKey("semesters.id"))
    week_start_date = Column(Date, nullable=False)
    week_number = Column(Integer, nullable=False)
    parity = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Group(Base):
    __tablename__ = "groups"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    department_id = Column(GUID(), ForeignKey("departments.id"))
    group_code = Column(String, nullable=False)
    academic_semester = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    acronym = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    designation = Column(String, nullable=True)
    home_department_id = Column(GUID(), ForeignKey("departments.id"), nullable=True)
    mobile_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_adjunct = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Room(Base):
    __tablename__ = "rooms"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    room_code = Column(String, unique=True, nullable=False)
    building = Column(String, nullable=True)
    is_lab = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TimeSlot(Base):
    __tablename__ = "time_slots"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    semester_id = Column(GUID(), ForeignKey("semesters.id"))
    slot_order = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Course(Base):
    __tablename__ = "courses"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    course_code = Column(String, unique=True, nullable=False)
    course_name = Column(String, nullable=True)
    credit_hours = Column(Numeric, nullable=True)
    department_id = Column(GUID(), ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ClassRoutine(Base):
    __tablename__ = "class_routines"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    semester_id = Column(GUID(), ForeignKey("semesters.id"))
    department_id = Column(GUID(), ForeignKey("departments.id"))
    group_id = Column(GUID(), ForeignKey("groups.id"))
    course_id = Column(GUID(), ForeignKey("courses.id"))
    teacher_id = Column(GUID(), ForeignKey("teachers.id"), nullable=True)
    room_id = Column(GUID(), ForeignKey("rooms.id"), nullable=True)
    time_slot_id = Column(GUID(), ForeignKey("time_slots.id"))
    day_of_week = Column(String, nullable=False)
    week_parity = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OnlineClass(Base):
    __tablename__ = "online_classes"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    semester_id = Column(GUID(), ForeignKey("semesters.id"))
    department_id = Column(GUID(), ForeignKey("departments.id"))
    group_id = Column(GUID(), ForeignKey("groups.id"))
    course_id = Column(GUID(), ForeignKey("courses.id"))
    teacher_id = Column(GUID(), ForeignKey("teachers.id"), nullable=True)
    day_of_week = Column(String, nullable=False)
    time_start = Column(Time, nullable=False)
    time_end = Column(Time, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ExamRoutine(Base):
    __tablename__ = "exam_routines"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    semester_id = Column(GUID(), ForeignKey("semesters.id"))
    department_id = Column(GUID(), ForeignKey("departments.id"))
    academic_semester = Column(Integer, nullable=False)
    course_id = Column(GUID(), ForeignKey("courses.id"))
    exam_date = Column(Date, nullable=False)
    day_of_week = Column(String, nullable=True)
    time_slot = Column(String, nullable=True)
    room_id = Column(GUID(), ForeignKey("rooms.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Override(Base):
    __tablename__ = "overrides"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    table_name = Column(String, nullable=False)
    record_id = Column(GUID(), nullable=False)
    field_name = Column(String, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    changed_by = Column(GUID(), ForeignKey("admin_users.id"))
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String, nullable=True)
    approved_pending_change_id = Column(GUID(), nullable=True)

class PendingChange(Base):
    __tablename__ = "pending_changes"
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    upload_batch_id = Column(GUID(), nullable=False)
    department_id = Column(GUID(), ForeignKey("departments.id"))
    semester_id = Column(GUID(), ForeignKey("semesters.id"), nullable=True)
    source_type = Column(String, nullable=False)
    table_name = Column(String, nullable=False)
    record_id = Column(GUID(), nullable=True)
    change_type = Column(String, nullable=False)
    field_name = Column(String, nullable=True)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    old_snapshot = Column(JSON, nullable=True)
    new_snapshot = Column(JSON, nullable=True)
    has_conflict = Column(Boolean, default=False)
    conflict_note = Column(String, nullable=True)
    status = Column(String, nullable=False)
    reviewed_by = Column(GUID(), ForeignKey("admin_users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
