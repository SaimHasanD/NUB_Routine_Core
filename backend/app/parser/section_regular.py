from openpyxl.worksheet.worksheet import Worksheet
from .merge_resolver import get_cell_value
from .section_utils import extract_row_entries

def parse_regular_section(ws: Worksheet, time_slots: dict, merge_map: dict, start_row: int, end_row: int) -> list[dict]:
    """
    Iterates rows from start_row to end_row. Each row = one room.
    For every time slot column, parses cell content.
    Returns list of raw schedule entries.
    """
    entries = []

    for row_idx in range(start_row, end_row + 1):
        room_val = get_cell_value(ws, row_idx, 1, merge_map)
        if room_val and isinstance(room_val, str):
            room = room_val.strip().replace("\n", " ")
        else:
            room = "TBA"

        base_props = {
            "room": room,
            "section_type": "regular",
            "week_note": "",
        }
        
        row_entries = extract_row_entries(ws, merge_map, row_idx, time_slots, base_props)
        entries.extend(row_entries)

    return entries
