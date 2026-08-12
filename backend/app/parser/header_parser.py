import re
from openpyxl.worksheet.worksheet import Worksheet

TIME_HEADER_ROW = 4
ROOM_COL = 1  # column A

TIME_RE = re.compile(r"\d{1,2}[:\.]\d{2}")


def parse_time_headers(ws: Worksheet) -> dict:
    """
    Returns {col_index: "8:00-8:50", ...} from row 4.
    Only columns that look like time slots are included.
    """
    slots = {}
    for cell in ws[TIME_HEADER_ROW]:
        if cell.value and isinstance(cell.value, str):
            val = cell.value.strip()
            if TIME_RE.search(val):
                # Normalize spacing around dash
                val = re.sub(r"\s*[-–—]\s*", "-", val).strip()
                slots[cell.column] = val
    return slots


def parse_online_time_headers(ws: Worksheet, header_row: int) -> dict:
    """Same logic but for the online section's header row."""
    slots = {}
    for cell in ws[header_row]:
        if cell.value and isinstance(cell.value, str):
            val = cell.value.strip()
            if TIME_RE.search(val):
                val = re.sub(r"\s*[-–—]\s*", "-", val).strip()
                # Expand merged range across columns
                slots[cell.column] = val
    return slots
