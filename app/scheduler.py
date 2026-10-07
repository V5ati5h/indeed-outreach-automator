"""Single scheduled pass: sync -> enrich -> score -> queue -> export -> audit log."""
from __future__ import annotations
import json
from datetime import datetime
from app import config
from app.database import get_db, init_db
from app.indeed import fetch_applications, load_cached, parse_applications, sync_applications
from app.enrichment import enrich_company
from app.outreach import score_lead, email_subject, email_body, whatsapp_body, first_name, queue_email, queue_whatsapp
from app.exports.csv_export import export_csv
from app.exports.migrate import migrate

LEGACY_CSV = config.BASE_DIR / "assets" / "job_leads.csv"
if not LEGACY_CSV.exists() and (config.BASE_DIR / "job_leads.csv").exists():
    LEGACY_CSV = config.BASE_DIR / "job_leads.csv"  # ponytail: backward-compat until move done

def run_cycle(offline: bool = False, enrich: bool = True) -> dict:
    init_db()
    if offline:
        raw = load_cached()
    else:
        raw = fetch_applications()
        # ponytail: snapshot every live fetch so offline sync always has a fixture
        (config.BASE_DIR / "indeed_applications.json").write_text(json.dumps(raw), encoding="utf-8")
    apps = parse_applications(raw)
    with get_db() as conn:
        # ponytail: root job_leads.csv is a live collect source, re-ingested idempotently every cycle
        csv_stats = migrate(conn, str(LEGACY_CSV)) if LEGACY_CSV.exists() else {"companies_added": 0, "contacts_added": 0}
        stats = sync_applications(conn, apps)
        queued_e = queued_w = 0
        for a in conn.execute("SELECT * FROM indeed_applications").fetchall():
            app = dict(a)
            co = conn.execute("SELECT * FROM companies WHERE id=?", (app["company_id"],)).fetchone()
            if enrich:
                enrich_company(conn, app["company_id"])
            contact = conn.execute("SELECT * FROM contacts WHERE company_id=? ORDER BY confidence LIMIT 1", (app["company_id"],)).fetchone()
            ct = dict(contact) if contact else None
            s, grade, _ = score_lead(app, ct, conn)
            if grade == "HOLD":
                continue
            exists = conn.execute("SELECT 1 FROM outreach_messages WHERE application_id=?", (app["id"],)).fetchone()
            if exists:
                continue
            nm = first_name((ct or {}).get("name", ""), (ct or {}).get("email", ""))
            if ct and ct.get("email"):
                queue_email(conn, app["company_id"], ct["id"], app["id"],
                            email_subject(app["job_title"]),
                            email_body(nm, co["name"], app["job_title"], app["location"], app["job_url"]))
                queued_e += 1
            if ct and ct.get("phone"):
                queue_whatsapp(conn, app["company_id"], ct["id"], app["id"],
                               whatsapp_body(nm, co["name"], app["job_title"], app["location"]))
                queued_w += 1
        n = export_csv(conn, str(config.EXPORTS_DIR / "job_leads.csv"))
    out = {**stats, "csv_companies_added": csv_stats["companies_added"],
             "csv_contacts_added": csv_stats["contacts_added"],
             "queued_emails": queued_e, "queued_whatsapp": queued_w, "exported": n}
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    (config.LOGS_DIR / f"{ts}_sync.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
