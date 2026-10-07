"""Indeed collector. Reuses v1 request shape. Cookie from .env only."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import requests
from app import config

def fetch_applications() -> list[dict[str, Any]]:
    if not config.INDEED_COOKIE:
        raise RuntimeError("INDEED_COOKIE missing. Put browser Cookie header in .env.")
    params = {"type": "POST_APPLY", "applyUpdateStartTime": config.APPLY_UPDATE_START_TIME, "from": "app-tracker"}
    if config.INDEED_TK:
        params["tk"] = config.INDEED_TK
    r = requests.get(config.INDEED_URL, params=params, headers={
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://myjobs.indeed.com/applied?from=_atweb_nc_application_updates",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/154.0.0.0 Safari/537.36",
        "Cookie": config.INDEED_COOKIE}, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status()
    jobs = r.json().get("body", {}).get("appStatusJobs", []) if isinstance(r.json(), dict) else []
    if not isinstance(jobs, list):
        raise ValueError("Unexpected Indeed response format.")
    return jobs

def load_cached(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or (config.BASE_DIR / "indeed_applications.json")
    payload = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    jobs = payload.get("body", {}).get("appStatusJobs", [])
    if isinstance(jobs, list):
        return jobs
    raise ValueError("Cached JSON has no appStatusJobs.")
