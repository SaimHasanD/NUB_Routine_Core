import asyncio
from datetime import datetime, timezone

_lock = asyncio.Lock()

_state: dict = {
    "title": None,
    "season": None,
    "odd_week_dates": [],
    "even_week_dates": [],
    "groups": [],
    "index": {},
    "total": 0,
}

# Metadata about the currently loaded routine file
_routine_meta: dict = {
    "filename": None,
    "uploaded_at": None,
    "groups_count": 0,
    "total_entries": 0,
}


async def set_state(data: dict, filename: str = None):
    async with _lock:
        _state["title"] = data.get("title")
        _state["season"] = data.get("season")
        _state["odd_week_dates"] = data.get("odd_week_dates", [])
        _state["even_week_dates"] = data.get("even_week_dates", [])
        _state["groups"] = data["groups"]
        _state["index"]  = data["index"]
        _state["total"]  = data["total"]
        _routine_meta["filename"] = filename
        _routine_meta["uploaded_at"] = datetime.now(timezone.utc).isoformat()
        _routine_meta["groups_count"] = len(data["groups"])
        _routine_meta["total_entries"] = data["total"]


async def get_state() -> dict:
    async with _lock:
        return dict(_state)


async def get_routine_meta() -> dict:
    async with _lock:
        return dict(_routine_meta)





def is_loaded() -> bool:
    return bool(_state["groups"])
