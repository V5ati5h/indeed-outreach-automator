"""SMTP sender with approval gate + logging. DRY_RUN=1 queues only."""
from __future__ import annotations
import hashlib, smtplib, sqlite3
from email.message import EmailMessage
from pathlib import Path
from app import config

def resume_info() -> tuple[str, str]:
    p = config.RESUME_PATH
    if not p.exists():
        return "", ""
    return str(p), hashlib.sha256(p.read_bytes()).hexdigest()[:16]

def queue_email(conn: sqlite3.Connection, company_id: int, contact_id: int, app_id: int,
                subject: str, body: str) -> int:
    path, h = resume_info()
    cur = conn.execute("""INSERT INTO outreach_messages(company_id,contact_id,application_id,channel,status,subject,body,attachment_path,attachment_hash)
     VALUES(?,?,?, 'EMAIL','QUEUED',?,?,?,?)""", (company_id, contact_id, app_id, subject, body, path, h))
    conn.commit()
    return cur.lastrowid

def send_approved(msg_id: int, db_path: Path | None = None) -> bool:
    """Send one APPROVED message. Returns True on success. DRY_RUN refuses."""
    from app.database import get_db
    if config.DRY_RUN:
        raise RuntimeError("DRY_RUN=1: approve in dashboard, set DRY_RUN=0 to actually send.")
    if not all([config.SMTP_HOST, config.SMTP_USERNAME, config.SMTP_FROM]):
        raise RuntimeError("SMTP not configured. See .env.example.")
    with get_db(db_path) as conn:
        m = conn.execute("""SELECT m.*, c.email FROM outreach_messages m
         LEFT JOIN contacts c ON c.id=m.contact_id WHERE m.id=?""", (msg_id,)).fetchone()
        if not m or not m["email"] or m["status"] != "APPROVED":
            raise ValueError("Message must be APPROVED with a contact email.")
        em = EmailMessage()
        em["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_FROM}>"
        em["To"] = m["email"]
        em["Subject"] = m["subject"]
        if config.SMTP_REPLY_TO: em["Reply-To"] = config.SMTP_REPLY_TO
        em.set_content(m["body"])
        if m["attachment_path"] and Path(m["attachment_path"]).exists():
            em.add_attachment(Path(m["attachment_path"]).read_bytes(),
                maintype="application", subtype="pdf",
                filename=Path(m["attachment_path"]).name)
        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
                s.starttls()
                s.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                s.send_message(em)
            conn.execute("UPDATE outreach_messages SET status='SENT', sent_at=datetime('now'), error='' WHERE id=?", (msg_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.execute("UPDATE outreach_messages SET status='FAILED', error=? WHERE id=?", (str(e)[:500], msg_id))
            conn.commit()
            return False
