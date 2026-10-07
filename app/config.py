"""Central settings. stdlib only. Never log secrets."""
from __future__ import annotations
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", BASE_DIR / "exports"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", BASE_DIR / "logs"))
ASSETS_DIR = Path(os.getenv("ASSETS_DIR", BASE_DIR / "assets"))

DB_PATH = Path(os.getenv("OUTREACH_DB", DATA_DIR / "outreach.db"))
RESUME_PATH = Path(os.getenv("RESUME_PATH", ASSETS_DIR / "Satish_Vishwakarma_Resume.pdf"))

INDEED_URL = os.getenv("INDEED_URL", "https://myjobs.indeed.com/api/v1/appStatusJobs")
INDEED_TK = os.getenv("INDEED_TK", "")
INDEED_COOKIE = os.getenv("INDEED_COOKIE", "")  # ponytail: cookie stays in .env only, never logged/stored
APPLY_UPDATE_START_TIME = os.getenv("APPLY_UPDATE_START_TIME", "0")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
ALLOW_CLOSED_JOBS = os.getenv("ALLOW_CLOSED_JOBS", "0") == "1"

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Satish | Traction Shastra")
SMTP_REPLY_TO = os.getenv("SMTP_REPLY_TO", SMTP_FROM)

MAX_FOLLOWUPS = int(os.getenv("MAX_FOLLOWUPS", "2"))
FOLLOWUP_DELAY_DAYS = int(os.getenv("FOLLOWUP_DELAY_DAYS", "5"))
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"  # safe default: queue, don't send
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8787"))

for d in (DATA_DIR, EXPORTS_DIR, LOGS_DIR, ASSETS_DIR):
    d.mkdir(parents=True, exist_ok=True)
