"""Ingest assets/job_leads.csv into SQLite (idempotent). Runs every sync cycle as a collect source."""
from __future__ import annotations
import csv, sqlite3
from app.indeed.parser import normalize_company
from app.enrichment import save_contact

def migrate(conn: sqlite3.Connection, csv_path: str) -> dict:
    n_co = n_ct = 0
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("Company") or "").strip()
            norm = normalize_company(name)
            if not norm:
                continue
            ex = conn.execute("SELECT id FROM companies WHERE normalized_name=?", (norm,)).fetchone()
            if ex:
                cid = ex["id"]
            else:
                cid = conn.execute("INSERT INTO companies(name,normalized_name,website,location,careers_url) VALUES(?,?,?,?,?)",
                    (name, norm, row.get("Website") or "", row.get("Location") or "", row.get("Careers URL") or "")).lastrowid
                n_co += 1
            email, phone = (row.get("Email") or "").strip(), (row.get("Phone") or "").strip()
            if email or phone:
                before = conn.execute("SELECT COUNT(*) c FROM contacts WHERE company_id=?", (cid,)).fetchone()["c"]
                save_contact(conn, cid, email=email, phone=phone, name=(row.get("Lead Name") or "").strip(),
                             source="job_leads.csv migration", role=(row.get("Contact Type") or ""))
                after = conn.execute("SELECT COUNT(*) c FROM contacts WHERE company_id=?", (cid,)).fetchone()["c"]
                n_ct += after - before
    conn.commit()
    return {"companies_added": n_co, "contacts_added": n_ct}
