from openpyxl import Workbook

FACULTY_SHEET = "Faculty Information"


def build_faculty_map(wb: Workbook) -> dict:
    """
    Returns {acronym: {name, designation, department, mobile, email}}
    Reads from 'Faculty Information' sheet.
    Falls back to empty dict if sheet is missing.
    """
    if FACULTY_SHEET not in wb.sheetnames:
        return {}

    ws = wb[FACULTY_SHEET]
    faculty = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        # Actual columns: S.L | Name | Acronym | Designation | Department | Mobile | Email
        if not row or not row[2]:
            continue

        acro = str(row[2]).strip().upper()
        faculty[acro] = {
            "name":        str(row[1]).strip() if row[1] else "",
            "designation": str(row[3]).strip() if row[3] else "",
            "department":  str(row[4]).strip() if row[4] else "",
            "mobile":      str(row[5]).strip() if row[5] else "",
            "email":       str(row[6]).strip() if row[6] else "",
        }

    return faculty


def resolve_teacher(acro: str, faculty_map: dict) -> dict:
    clean_acro = acro.strip().upper()
    if not clean_acro:
        return {
            "name":        "TBA",
            "designation": "To Be Announced",
            "department":  "Department of CSE",
            "mobile":      "N/A",
            "email":       "N/A"
        }
    return faculty_map.get(clean_acro, {"name": clean_acro, "designation": "", "department": "", "mobile": "", "email": ""})
