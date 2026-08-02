from pydantic import BaseModel


class Teacher(BaseModel):
    name: str
    designation: str
    department: str
    mobile: str
    email: str


class ScheduleEntry(BaseModel):
    course_code: str
    course: str
    group: str
    teacher_acro: str
    teacher: Teacher
    room: str
    time_slot: str
    start_time: str
    end_time: str
    day: str
    type: str
    odd_even: str | None = None
    section_type: str   # regular | lab_odd | lab_even | online | online_odd | online_even
    week_note: str


class UploadResponse(BaseModel):
    groups: list[str]
    total_entries: int
    title: str | None = None
    season: str | None = None
    odd_week_dates: list[str] = []
    even_week_dates: list[str] = []
    message: str


class GroupRoutineResponse(BaseModel):
    group: str
    title: str | None = None
    season: str | None = None
    odd_week_dates: list[str] = []
    even_week_dates: list[str] = []
    entries: list[ScheduleEntry]
