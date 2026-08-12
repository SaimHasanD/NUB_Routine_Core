from openpyxl.worksheet.worksheet import Worksheet
from .merge_resolver import get_cell_value
from .cell_parser import parse_cell

def extract_row_entries(
    ws: Worksheet,
    merge_map: dict,
    row_idx: int,
    time_slots: dict,
    base_props: dict,
    col_start: int = 1,
    entry_modifier = None
) -> list[dict]:
    """
    Iterates over the time_slots columns for a given row, parsing cell contents.
    Injects base_props (like room, section_type) into each parsed entry.
    Calls entry_modifier(entry, col_idx) if provided, for per-cell custom logic.
    """
    entries = []
    for col_idx, time_slot in time_slots.items():
        if col_idx < col_start:
            continue
        
        cell_val = get_cell_value(ws, row_idx, col_idx, merge_map)
        if not cell_val:
            continue

        parsed = parse_cell(str(cell_val))
        for p in parsed:
            entry = {
                **p,
                **base_props,
                "time_slot": time_slot
            }
            if entry_modifier:
                entry = entry_modifier(entry, col_idx)
            
            if entry:
                entries.append(entry)
                
    return entries
