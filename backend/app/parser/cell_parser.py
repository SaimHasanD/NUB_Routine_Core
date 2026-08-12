import re

SKIP_VALUES = {"makeup class", ""}

# Matches: CSE 1102 – 1B  or  CSE 4241-8A  or  MATH 1302-2C
COURSE_GROUP_RE = re.compile(
    r"([A-Z]+\s*\d{3,4})\s*[-–—]+\s*(\d+[A-Z])",
    re.IGNORECASE
)
TEACHER_RE = re.compile(r"#([A-Z0-9]+)", re.IGNORECASE)


def parse_cell(text: str) -> list[dict]:
    if not text:
        return []

    text = text.strip()
    if text.lower() in SKIP_VALUES:
        return []

    # Teacher acronym can be anywhere in the cell (often on its own line)
    teacher_match = TEACHER_RE.search(text)
    teacher_acro = teacher_match.group(1).strip().upper() if teacher_match else ""

    results = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        course_match = COURSE_GROUP_RE.search(line)
        if course_match:
            results.append({
                "course_code":  course_match.group(1).strip().upper(),
                "group":        course_match.group(2).strip().upper(),
                "teacher_acro": teacher_acro,
            })

    return results
