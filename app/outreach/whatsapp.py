"""WhatsApp = manual/approved only. No unattended automation (ToS)."""
from __future__ import annotations
import sqlite3
from .templates import wa_link

def queue_whatsapp(conn: sqlite3.Connection, company_id: int, contact_id: int, app_id: int, body: str) -> int:
    cur = conn.execute("""INSERT INTO outreach_messages(company_id,contact_id,application_id,channel,status,body)
     VALUES(?,?,?, 'WHATSAPP','QUEUED',?)""", (company_id, contact_id, app_id, body))
    conn.commit()
    return cur.lastrowid

def approve_whatsapp(conn: sqlite3.Connection, msg_id: int) -> str:
    """Human approves -> returns click-to-chat link. Sending happens in WhatsApp (official app/API)."""
    m = conn.execute("""SELECT m.*, c.phone FROM outreach_messages m
     LEFT JOIN contacts c ON c.id=m.contact_id WHERE m.id=?""", (msg_id,)).fetchone()
    if not m:
        raise ValueError("Message not found.")
    conn.execute("UPDATE outreach_messages SET status='APPROVED', queued_at=datetime('now') WHERE id=?", (msg_id,))
    conn.commit()
    return wa_link(m["phone"] or "", m["body"] or "")

def mark_sent(conn: sqlite3.Connection, msg_id: int) -> None:
    conn.execute("UPDATE outreach_messages SET status='SENT', sent_at=datetime('now') WHERE id=?", (msg_id,))
    conn.commit()
