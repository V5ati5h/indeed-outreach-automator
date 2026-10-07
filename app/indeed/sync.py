"""Upsert applications + companies. New/changed detection only."""
from __future__ import annotations
import sqlite3
from .parser import normalize_company

def sync_applications(conn: sqlite3.Connection, apps: list[dict]) -> dict:
    new_apps = upd_apps = new_cos = 0
    for a in apps:
        norm = normalize_company(a["company"])
        if not norm:
            continue
        row = conn.execute("SELECT id FROM companies WHERE normalized_name=?", (norm,)).fetchone()
        if row:
            cid = row["id"]
            conn.execute("UPDATE companies SET name=COALESCE(NULLIF(name,''),?), updated_at=datetime('now') WHERE id=?", (a["company"], cid))
        else:
            cur = conn.execute("INSERT INTO companies(name, normalized_name, location) VALUES(?,?,?)",
                               (a["company"], norm, a.get("location", "")))
            cid = cur.lastrowid
            new_cos += 1
        ex = conn.execute("SELECT * FROM indeed_applications WHERE indeed_job_key=?", (a["indeed_job_key"],)).fetchone()
        if ex:
            conn.execute("""UPDATE indeed_applications SET company_id=?, job_title=?, job_url=?, location=?,
             candidate_status=?, employer_status=?, apply_time=?, job_expired=?, withdrawn=?, job_fraudulent=?,
             messaging_available=?, last_seen_at=datetime('now') WHERE indeed_job_key=?""",
             (cid, a["job_title"], a["job_url"], a["location"], a["candidate_status"], a["employer_status"],
              a["apply_time"], a["job_expired"], a["withdrawn"], a["job_fraudulent"], a["messaging_available"], a["indeed_job_key"]))
            upd_apps += 1
        else:
            conn.execute("""INSERT INTO indeed_applications(company_id, indeed_job_key, job_title, job_url, location,
             candidate_status, employer_status, apply_time, job_expired, withdrawn, job_fraudulent, messaging_available)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
             (cid, a["indeed_job_key"], a["job_title"], a["job_url"], a["location"], a["candidate_status"],
              a["employer_status"], a["apply_time"], a["job_expired"], a["withdrawn"], a["job_fraudulent"], a["messaging_available"]))
            new_apps += 1
    conn.execute("INSERT INTO sync_runs(new_apps, updated_apps, new_companies) VALUES(?,?,?)", (new_apps, upd_apps, new_cos))
    conn.commit()
    return {"new_apps": new_apps, "updated_apps": upd_apps, "new_companies": new_cos}
