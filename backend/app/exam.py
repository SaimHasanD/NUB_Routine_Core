import base64
import json
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Form

try:
    from .shared import (
        ADMIN_PASSWORD, GEMINI_API_KEY, SUPABASE_BUCKET,
        EXAM_SCHEDULE_FILENAME, supabase_client, logger,
    )
    from .state import get_state
except ImportError:
    from shared import (
        ADMIN_PASSWORD, GEMINI_API_KEY, SUPABASE_BUCKET,
        EXAM_SCHEDULE_FILENAME, supabase_client, logger,
    )
    from state import get_state

router = APIRouter()


GEMINI_EXAM_PROMPT = """\
You are extracting a university exam schedule table from an image into structured JSON.

This table has TWO separate things you must extract independently: (1) the header
structure, and (2) the row data by physical column position. Do NOT try to match
row data to header labels yourself — that will be done afterward in code. Your
only job is accurate transcription of what is physically printed.

PART 1 — HEADER MAP:
The table has exactly 3 physical column positions (left to right: position 0,
position 1, position 2) under the "Exam Day" row. Different day-types use
different subsets of these 3 positions — some days only have data in 1 or 2 of
the 3 positions, with the rest shown as blank or "×".
Above the table, there is a merged header block showing slot labels and time
ranges for each day-type (e.g. Friday, Saturday, Sunday & Monday). Read that
header block and produce a map: for each day-of-week name, list exactly 3
entries — one per physical position (0, 1, 2) — using the exact label+time text
printed for that day-type at that position, or null if that day-type has no
column at that position at all (structurally absent, not just empty).

PART 2 — ROW DATA:
For each exam day row, read the date and day name exactly as printed (do not
calculate or correct them). Then read the course codes present at each of the 3
physical column positions for that row, left to right, in the order printed.
- If a cell is empty or shows "×", its position's course list is [].
- CAUTION: rows where most columns show "×" still often have real course data
  in the one remaining column — do not assume a row is fully empty just because
  most of its columns are "×". Check every column position individually, even
  when the other columns in that row are marked "×".
- If a day's row has no column at a position at all, still include that
  position as [] in the "columns" array (code will decide whether to keep it,
  using the header map from Part 1).
- Extract ONLY the course code for each course (e.g. "CSE 4136"), not the
  course name or any parenthetical numbers that follow it in the cell.
- Never copy a course list from one row/position into another.

OUTPUT FORMAT:
Return ONLY a JSON object, no explanation, no markdown fences, no trailing text.
{
  "header_map": {
    "Friday":   ["1st Slot (10:30 am - 12:00 pm)", "2nd Slot (2:30 pm - 4:00 pm)", "3rd Slot (4:30 pm - 6:00 pm)"],
    "Saturday": ["1st Slot (4:30 pm - 6:00 pm)", "2nd Slot (6:30 pm - 8:00 pm)", null],
    "Sunday":   [null, null, "2nd Slot (6:00 pm - 7:30 pm)"],
    "Monday":   [null, null, "2nd Slot (6:00 pm - 7:30 pm)"]
  },
  "rows": [
    {
      "date": "10/07/2026",
      "day": "Friday",
      "columns": [["CSE 4136"], [], ["MATH 2204"]]
    }
  ]
}
"""


def _clean_course_code(raw: str) -> str:
    """
    Gemini sometimes returns the full cell text ('PHY 1201: Physics I (Heat...) (1)')
    instead of just the code. Extract only the leading course-code token so
    semester lookup and display stay consistent regardless of what Gemini returns.
    """
    import re
    match = re.match(r"^\s*([A-Z]{2,4}\s*\d{3,4})", raw.strip().upper())
    return match.group(1).strip() if match else raw.strip()


def _assemble_schedule(header_map: dict, rows: list[dict]) -> list[dict]:
    """
    Deterministically joins Gemini's positional row data with its header map.
    This replaces asking Gemini to pick the correct slot label itself — that
    repeatedly caused mislabeled slots. Position-to-label assignment is now a
    plain lookup in code, which cannot drift or hallucinate.
    """
    schedule = []
    for row in rows:
        day = (row.get("day") or "").strip()
        date = row.get("date")
        columns = row.get("columns") or []
        labels = header_map.get(day, [None, None, None])

        for position, courses in enumerate(columns):
            if position >= len(labels):
                continue
            label = labels[position]
            if label is None:
                # This day-type has no real column at this position — skip entirely.
                continue
            cleaned = [_clean_course_code(c) for c in (courses or [])]
            schedule.append({
                "date": date,
                "day": day,
                "slot": label,
                "courses": cleaned,
            })
    return schedule


def _lookup_semester(course_code: str | dict, index: dict) -> int | None:
    """
    Search all groups in the in-memory routine index for the given course_code.
    Return the semester number from the group ID's leading digit (e.g. '1B' -> 1),
    or None if not found. Group IDs always share the same courses within a
    semester (1A-1F etc.), so the first match is authoritative.
    """
    import re

    if isinstance(course_code, dict):
        course_code = course_code.get("code", "")

    normalized = re.sub(r"\s+", " ", course_code.strip().upper())
    for group_id, entries in index.items():
        for entry in entries:
            ec = re.sub(r"\s+", " ", (entry.get("course_code") or "").strip().upper())
            if ec == normalized:
                m = re.search(r"^(\d+)", group_id)
                if m:
                    return int(m.group(1))
    return None


def _dedupe_and_validate(exam_entries: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Code-side safety net. Gemini can occasionally:
    (a) emit the same (date, day, slot) combination more than once, or
    (b) copy one row's course list into a different row/slot's output.
    Real exam schedules never repeat the same slot, and never show the exact
    same set of 2+ courses under two different (date, slot) pairs.
    This runs deterministic checks in code rather than trusting the model's
    self-check instruction alone.
    """
    warnings: list[str] = []
    seen_keys = set()
    deduped = []

    for entry in exam_entries:
        key = (entry.get("date"), entry.get("day"), entry.get("slot"))
        if key in seen_keys:
            warnings.append(f"Duplicate slot skipped: {key}")
            continue
        seen_keys.add(key)
        deduped.append(entry)

    course_set_map: dict[tuple, list[tuple]] = {}
    for entry in deduped:
        courses = entry.get("courses") or []
        codes = tuple(sorted(
            c["code"] if isinstance(c, dict) else c
            for c in courses
        ))
        if len(codes) >= 2:
            course_set_map.setdefault(codes, []).append(
                (entry.get("date"), entry.get("slot"))
            )

    for codes, locations in course_set_map.items():
        if len(locations) > 1:
            warnings.append(
                f"Same course set {codes} appears in multiple slots {locations} "
                f"— likely extraction error, please verify against source image."
            )

    return deduped, warnings


@router.post("/api/v1/exam/upload")
async def upload_exam_schedule(
    file: UploadFile = File(...),
    password: str = Form(""),
):
    """Admin-only. Accept a JPG/PNG exam schedule image, extract structured JSON
    via Gemini Vision, validate/dedupe in code, enrich with semester numbers,
    and persist to Supabase."""
    if password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid admin password.")

    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY environment variable is not set.")

    filename_lower = (file.filename or "").lower()
    is_image = any(
        filename_lower.endswith(ext)
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")
    )
    if not is_image:
        raise HTTPException(400, "Only image files (.png, .jpg, .jpeg, .webp) are supported.")

    raw_bytes = await file.read()
    ext = Path(file.filename or "img.jpg").suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    mime_type = mime_map.get(ext, "image/jpeg")

    # ── Call Gemini Vision (new google-genai SDK) ──────────────────────────
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                types.Part.from_bytes(data=raw_bytes, mime_type=mime_type),
                GEMINI_EXAM_PROMPT,
            ],
        )
        raw_text = response.text.strip()
    except Exception as exc:
        raise HTTPException(502, f"Gemini API call failed: {exc}")

    # Extract only the JSON object portion to avoid trailing text errors
    first_brace = raw_text.find("{")
    last_brace = raw_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace >= first_brace:
        raw_text = raw_text[first_brace:last_brace + 1]
    elif raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(
            ln for ln in lines if not ln.strip().startswith("```")
        ).strip()

    try:
        gemini_output = json.loads(raw_text)
        if not isinstance(gemini_output, dict):
            raise ValueError("Expected a JSON object with header_map and rows.")
        header_map = gemini_output.get("header_map") or {}
        rows = gemini_output.get("rows") or []
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            422,
            f"Gemini returned invalid JSON: {exc}. Raw: {raw_text[:400]}",
        )

    # ── Assemble slot labels deterministically in code, not via the model ──
    exam_entries = _assemble_schedule(header_map, rows)

    # ── Code-side validation/dedup (do not trust the model alone) ──────────
    exam_entries, extraction_warnings = _dedupe_and_validate(exam_entries)
    for w in extraction_warnings:
        logger.warning(f"Exam extraction warning: {w}")

    # ── Enrich with semester numbers from in-memory routine ────────────────
    state = await get_state()
    routine_index = state.get("index", {})

    if not routine_index:
        raise HTTPException(409, "Routine not loaded — wait a moment and retry.")

    for entry in exam_entries:
        enriched_courses = []
        for course_code in (entry.get("courses") or []):
            sem = _lookup_semester(course_code, routine_index)
            enriched_courses.append({"code": course_code, "semester": sem})
        entry["courses"] = enriched_courses

    # ── Upload to Supabase ──────────────────────────────────────────────────
    if not supabase_client:
        raise HTTPException(500, "Supabase is not configured on this server.")

    image_filename = f"exam_schedule_image{ext}"
    try:
        try:
            supabase_client.storage.from_(SUPABASE_BUCKET).remove([image_filename])
        except Exception:
            pass
        supabase_client.storage.from_(SUPABASE_BUCKET).upload(
            image_filename,
            raw_bytes,
            file_options={"content-type": mime_type},
        )
        image_url = supabase_client.storage.from_(SUPABASE_BUCKET).get_public_url(image_filename)

        final_data = {
            "image_url": image_url,
            "schedule": exam_entries,
        }
        json_bytes = json.dumps(final_data, ensure_ascii=False, indent=2).encode("utf-8")

        try:
            supabase_client.storage.from_(SUPABASE_BUCKET).remove([EXAM_SCHEDULE_FILENAME])
        except Exception:
            pass

        supabase_client.storage.from_(SUPABASE_BUCKET).upload(
            EXAM_SCHEDULE_FILENAME,
            json_bytes,
            file_options={"content-type": "application/json"},
        )
        logger.info(f"Exam schedule uploaded to Supabase as '{EXAM_SCHEDULE_FILENAME}' "
                    f"({len(exam_entries)} entries)")
    except Exception as exc:
        raise HTTPException(502, f"Failed to upload exam schedule to Supabase: {exc}")

    return {
        "success": True,
        "entries": len(exam_entries),
        "warnings": extraction_warnings,
    }


@router.get("/api/v1/exam")
async def get_exam_schedule():
    """Public. Downloads exam_schedule.json from Supabase and returns it."""
    if not supabase_client:
        raise HTTPException(500, "Supabase is not configured on this server.")

    try:
        file_bytes = supabase_client.storage.from_(SUPABASE_BUCKET).download(
            EXAM_SCHEDULE_FILENAME
        )
    except Exception:
        raise HTTPException(404, "No exam schedule uploaded yet")

    if not file_bytes:
        raise HTTPException(404, "No exam schedule uploaded yet")

    try:
        data = json.loads(file_bytes)
    except Exception as exc:
        raise HTTPException(500, f"Failed to parse exam schedule from Supabase: {exc}")

    return data
