"""SQLite schema + helpers. stdlib sqlite3 only."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies(
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT NOT NULL UNIQUE,
 website TEXT DEFAULT '', location TEXT DEFAULT '', linkedin_url TEXT DEFAULT '',
 careers_url TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS contacts(
 id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id),
 name TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '', role TEXT DEFAULT '',
 source TEXT DEFAULT '', confidence TEXT DEFAULT 'UNKNOWN', verified_at TEXT,
 UNIQUE(company_id, email, phone));
CREATE TABLE IF NOT EXISTS indeed_applications(
 id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id),
 indeed_job_key TEXT UNIQUE, job_title TEXT DEFAULT '', job_url TEXT DEFAULT '',
 location TEXT DEFAULT '', candidate_status TEXT DEFAULT '', employer_status TEXT DEFAULT '',
 apply_time TEXT DEFAULT '', job_expired INTEGER DEFAULT 0, withdrawn INTEGER DEFAULT 0,
 job_fraudulent INTEGER DEFAULT 0, messaging_available INTEGER DEFAULT 0,
 first_seen_at TEXT DEFAULT (datetime('now')), last_seen_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS outreach_messages(
 id INTEGER PRIMARY KEY, company_id INTEGER, contact_id INTEGER, application_id INTEGER,
 channel TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'QUEUED',
 subject TEXT DEFAULT '', body TEXT DEFAULT '', attachment_path TEXT DEFAULT '',
 attachment_hash TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now')),
 queued_at TEXT DEFAULT (datetime('now')), sent_at TEXT, provider_message_id TEXT DEFAULT '',
 error TEXT DEFAULT '', followup_n INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS suppression_list(
 id INTEGER PRIMARY KEY, email TEXT DEFAULT '', phone TEXT DEFAULT '', company TEXT DEFAULT '',
 reason TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS sync_runs(
 id INTEGER PRIMARY KEY, started_at TEXT DEFAULT (datetime('now')),
 new_apps INTEGER DEFAULT 0, updated_apps INTEGER DEFAULT 0, new_companies INTEGER DEFAULT 0, note TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS idx_msg_status ON outreach_messages(status, channel);
CREATE INDEX IF NOT EXISTS idx_app_company ON indeed_applications(company_id);
"""

def get_db(path: Path | None = None) -> sqlite3.Connection:
    p = path or config.DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c

def init_db(path: Path | None = None) -> Path:
    p = path or config.DB_PATH
    with get_db(p) as c:
        c.executescript(SCHEMA)
    return p
