"""Lead scoring: A/B/C/HOLD. Suppression = hard block."""
from __future__ import annotations
import sqlite3

def score_lead(app: dict, contact: dict | None, conn: sqlite3.Connection | None = None) -> tuple[int, str, list[str]]:
    s, why = 0, []
    def add(p: int, r: str):
        nonlocal s
        s += p
        why.append(f"{r}:{p:+d}")
    if app.get("employer_status") == "OPEN": add(30, "job_open")
    if app.get("employer_status") == "CLOSED": add(-50, "job_closed")
    if str(app.get("apply_time", ""))[:4] >= "2025": add(20, "recent")
    jt = (app.get("job_title") or "").lower()
    if any(k in jt for k in ("laravel", "php", "wordpress", "full stack", "full-stack", "backend", "web developer")):
        add(20, "role_match")
    if contact:
        if contact.get("role") == "PUBLIC_HR_EMAIL": add(15, "hr_email")
        if contact.get("name"): add(10, "named")
        if contact.get("phone"): add(5, "phone")
    if app.get("candidate_status") in ("REJECTED", "WITHDRAWN") or app.get("withdrawn"): return -100, "HOLD", ["blocked_status:-100"]
    if conn is not None:
        em, ph = (contact or {}).get("email", ""), (contact or {}).get("phone", "")
        if em and conn.execute("SELECT 1 FROM suppression_list WHERE email=?", (em,)).fetchone(): return -1000, "HOLD", ["optout:-1000"]
        if ph and conn.execute("SELECT 1 FROM suppression_list WHERE phone=?", (ph,)).fetchone(): return -1000, "HOLD", ["optout:-1000"]
        if app.get("id") and conn.execute(
            "SELECT 1 FROM outreach_messages WHERE application_id=? AND status IN ('SENT','QUEUED','APPROVED')", (app["id"],)).fetchone():
            add(-80, "already_queued")
    grade = "A" if s >= 80 else "B" if s >= 60 else "C" if s >= 40 else "HOLD"
    return s, grade, why
