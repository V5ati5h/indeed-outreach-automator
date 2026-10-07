"""Normalize Indeed appStatusJobs rows. Also hosts company dedup normalize."""
from __future__ import annotations
import re
from typing import Any

def normalize_company(v: str) -> str:
    v = (v or "").lower().replace("&", " and ")
    v = re.sub(r"[^a-z0-9]+", " ", v)
    v = re.sub(r"\b(private limited|pvt ltd|pvt|private|limited|ltd|llp|incorporated|inc|technologies|technology|solutions|systems|services)\b", " ", v)
    # ponytail: keep suffix-strip light; aggressive strip merges distinct firms. Full alias table only if collisions seen.
    v = re.sub(r"\b(private limited|pvt ltd|pvt|private|limited|ltd|llp|incorporated|inc)\b", " ", v)
    return re.sub(r"\s+", " ", v).strip()

def _job_key(app: dict) -> str:
    for k in ("jobKey", "jk", "jobId"):
        if app.get(k):
            return str(app[k])
    m = re.search(r"[?&]jk=([A-Za-z0-9]+)", app.get("jobUrl", "") or "")
    return m.group(1) if m else f"{normalize_company((app.get('company') or {}).get('name',''))}|{app.get('jobTitle','')}"[:120]

def parse_applications(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for a in raw:
        st = a.get("statuses") or {}
        out.append({
            "indeed_job_key": _job_key(a),
            "company": ((a.get("company") or {}).get("name") or "").strip(),
            "job_title": a.get("jobTitle") or "",
            "job_url": a.get("jobUrl") or "",
            "location": (a.get("jobLocation") or a.get("location") or "") if isinstance(a.get("jobLocation"), str) else "",
            "candidate_status": (st.get("candidateStatus") or {}).get("status", "").upper(),
            "employer_status": (st.get("employerJobStatus") or {}).get("status", "").upper(),
            "apply_time": str(a.get("applyTime") or a.get("appliedAt") or ""),
            "job_expired": int(bool(a.get("jobExpired"))),
            "withdrawn": int(bool(a.get("withdrawn"))),
            "job_fraudulent": int(bool(a.get("jobFraudulent"))),
            "messaging_available": int(bool((a.get("messaging") or {}).get("available", a.get("messagingAvailable", False)))),
        })
    return out
