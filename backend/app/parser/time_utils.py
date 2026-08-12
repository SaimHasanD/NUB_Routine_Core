def normalize_to_24h(t_str: str) -> str:
    s = t_str.strip().upper()
    if not s:
        return "00:00"

    is_pm = "PM" in s
    is_am = "AM" in s

    s = s.replace("AM", "").replace("PM", "").strip()
    parts = s.split(":")
    if len(parts) < 2:
        try:
            h = int(parts[0])
            m = 0
        except ValueError:
            return "00:00"
    else:
        try:
            h = int(parts[0])
            m = int(parts[1])
        except ValueError:
            return "00:00"

    if is_pm:
        if h < 12:
            h += 12
    elif is_am:
        if h == 12:
            h = 0
    else:
        if 1 <= h <= 7:
            h += 12
        elif h == 12:
            pass

    return f"{h:02d}:{m:02d}"


def to_12h_format(t_24h: str) -> str:
    parts = t_24h.split(":")
    if len(parts) != 2:
        return t_24h
    try:
        h = int(parts[0])
        m = int(parts[1])
    except ValueError:
        return t_24h

    suffix = "AM"
    if h >= 12:
        suffix = "PM"
        if h > 12:
            h -= 12
    elif h == 0:
        h = 12

    return f"{h}:{m:02d} {suffix}"


def merge_consecutive_entries(entries: list[dict]) -> list[dict]:
    by_day = {}
    for e in entries:
        entry_copy = dict(e)
        entry_copy["start_time_24"] = normalize_to_24h(entry_copy.get("start_time", ""))
        entry_copy["end_time_24"] = normalize_to_24h(entry_copy.get("end_time", ""))
        by_day.setdefault(entry_copy.get("day"), []).append(entry_copy)

    merged_all = []
    for day, day_list in by_day.items():
        day_list.sort(key=lambda x: x["start_time_24"])

        merged_day = []
        for e in day_list:
            if not merged_day:
                merged_day.append(e)
                continue

            prev = merged_day[-1]

            prev_teacher_name = prev["teacher"]["name"] if isinstance(prev.get("teacher"), dict) else prev.get("teacher")
            curr_teacher_name = e["teacher"]["name"] if isinstance(e.get("teacher"), dict) else e.get("teacher")

            if (prev["course_code"] == e["course_code"] and
                prev_teacher_name == curr_teacher_name and
                prev["room"] == e["room"] and
                prev["end_time_24"] == e["start_time_24"]):

                prev["end_time_24"] = e["end_time_24"]
            else:
                merged_day.append(e)

        for e in merged_day:
            e["start_time"] = to_12h_format(e["start_time_24"])
            e["end_time"] = to_12h_format(e["end_time_24"])
            e["time_slot"] = f"{e['start_time']} – {e['end_time']}"
            e.pop("start_time_24", None)
            e.pop("end_time_24", None)

        merged_all.extend(merged_day)
    return merged_all
