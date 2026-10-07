"""Suppression + follow-up caps. STOP means STOP."""
from __future__ import annotations
import sqlite3
from app import config

def suppress(conn: sqlite3.Connection, email="", phone="", company="", reason="opt-out") -> None:
    conn.execute("INSERT INTO suppression_list(email,phone,company,reason) VALUES(?,?,?,?)", (email, phone, company, reason))
    conn.commit()

def is_suppressed(conn: sqlite3.Connection, email="", phone="") -> bool:
    if email and conn.execute("SELECT 1 FROM suppression_list WHERE email=?", (email,)).fetchone(): return True
    if phone and conn.execute("SELECT 1 FROM suppression_list WHERE phone=?", (phone,)).fetchone(): return True
    return False

def due_followups(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(f"""SELECT * FROM outreach_messages WHERE channel='EMAIL' AND status='SENT'
     AND followup_n < {config.MAX_FOLLOWUPS}
     AND julianday('now') - julianday(sent_at) >= {config.FOLLOWUP_DELAY_DAYS}
     AND NOT EXISTS (SELECT 1 FROM outreach_messages f WHERE f.application_id=outreach_messages.application_id AND f.followup_n > outreach_messages.followup_n)""").fetchall()
