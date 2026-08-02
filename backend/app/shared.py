import os
import logging
from pathlib import Path

logger = logging.getLogger("uvicorn.error")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123_nu")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "routine-files")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except ImportError:
        logger.warning("Supabase configured but 'supabase' library is not installed.")
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}")

# Persistent storage for the single active routine file
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

EXAM_SCHEDULE_FILENAME = "exam_schedule.json"
