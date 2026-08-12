from openpyxl.worksheet.worksheet import Worksheet
from .merge_resolver import get_cell_value
from .section_utils import extract_row_entries


ODD_MARKER    = "odd"
EVEN_MARKER   = "even"


def parse_lab_section(ws: Worksheet, time_slots: dict, merge_map: dict, start_row: int, end_row: int) -> list[dict]:
    """
    Lab rooms span 2 rows: odd week (row N) and even week (row N+1).
    Col A = room (merged across 2 rows), Col B = odd/even marker.
    """
    entries = []

    row_idx = start_row
    while row_idx <= end_row:
        room_val = get_cell_value(ws, row_idx, 1, merge_map)
        if room_val and isinstance(room_val, str):
            room = room_val.strip().replace("\n", " ")
        else:
            room = "TBA"

        for sub_row in [row_idx, row_idx + 1]:
            week_marker_val = get_cell_value(ws, sub_row, 2, merge_map) or ""
            week_marker = str(week_marker_val).strip().lower()

            if ODD_MARKER in week_marker:
                week_note = "Odd weeks only"
                section_type = "lab_odd"
            elif EVEN_MARKER in week_marker:
                week_note = "Even weeks only"
                section_type = "lab_even"
            else:
                week_note = ""
                section_type = "lab"

            base_props = {
                "room": room,
                "section_type": section_type,
                "week_note": week_note,
            }
            
            row_entries = extract_row_entries(
                ws, 
                merge_map, 
                sub_row, 
                time_slots, 
                base_props, 
                col_start=3
            )
            entries.extend(row_entries)

        row_idx += 2

    return entries
