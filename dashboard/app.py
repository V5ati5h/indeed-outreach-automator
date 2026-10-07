"""Single-page stdlib dashboard: sync controls + searchable queue + profile. No deps."""
from __future__ import annotations
import html
import os
import smtplib
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from app import config
from app.database import get_db, init_db
from app.outreach.templates import (
    wa_link, load_profile, save_profile, email_subject, email_body, whatsapp_body, first_name,
    DEFAULT_PROFILE,
)

FLASH = {"msg": "", "err": False}


def _live(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v is not None:
        return v
    try:
        for line in (config.BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return default


def _send_email(msg_id: int) -> str:
    if _live("DRY_RUN", "1") == "1":
        return "DRY_RUN=1: set DRY_RUN=0 in .env to actually send."
    host, user, pw = _live("SMTP_HOST"), _live("SMTP_USERNAME"), _live("SMTP_PASSWORD")
    frm, frm_name = _live("SMTP_FROM"), _live("SMTP_FROM_NAME", "Satish")
    port = int(_live("SMTP_PORT", "587") or 587)
    if not all([host, user, frm]):
        return "SMTP not configured. Fill SMTP_HOST/USERNAME/PASSWORD/FROM in .env."
    with get_db() as conn:
        m = conn.execute(
            "SELECT m.*, c.email FROM outreach_messages m LEFT JOIN contacts c ON c.id=m.contact_id WHERE m.id=?",
            (msg_id,)).fetchone()
        if not m or not m["email"]:
            return "No contact email on this message."
        if m["status"] not in ("APPROVED", "QUEUED"):
            return f"Status is {m['status']}; approve first."
        em = EmailMessage()
        em["From"] = f"{frm_name} <{frm}>" if frm_name else frm
        em["To"] = m["email"]
        em["Subject"] = m["subject"] or "(no subject)"
        reply = _live("SMTP_REPLY_TO", frm)
        if reply:
            em["Reply-To"] = reply
        em.set_content(m["body"] or "")
        if m["attachment_path"] and Path(m["attachment_path"]).exists():
            em.add_attachment(Path(m["attachment_path"]).read_bytes(), maintype="application",
                              subtype="pdf", filename=Path(m["attachment_path"]).name)
        try:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls()
                s.login(user, pw)
                s.send_message(em)
            conn.execute("UPDATE outreach_messages SET status='SENT', sent_at=datetime('now'), error='' WHERE id=?", (msg_id,))
            conn.commit()
            return ""
        except Exception as e:  # noqa: BLE001 — surfaced in UI
            conn.execute("UPDATE outreach_messages SET status='FAILED', error=? WHERE id=?", (str(e)[:500], msg_id))
            conn.commit()
            return str(e)[:300]


def _regen(mid: int) -> str:
    with get_db() as conn:
        m = conn.execute(
            "SELECT m.*, co.name co, a.job_title job, a.location loc, a.job_url url, c.name cname, c.email cem "
            "FROM outreach_messages m LEFT JOIN companies co ON co.id=m.company_id "
            "LEFT JOIN indeed_applications a ON a.id=m.application_id "
            "LEFT JOIN contacts c ON c.id=m.contact_id WHERE m.id=?", (mid,)).fetchone()
        if not m:
            return "Message not found."
        nm = first_name(m["cname"] or "", m["cem"] or "")
        if m["channel"] == "EMAIL":
            subj = email_subject(m["job"] or "")
            body = email_body(nm, m["co"] or "", m["job"] or "", m["loc"] or "", m["url"] or "")
            conn.execute("UPDATE outreach_messages SET subject=?, body=? WHERE id=?", (subj, body, mid))
        else:
            body = whatsapp_body(nm, m["co"] or "", m["job"] or "", m["loc"] or "")
            conn.execute("UPDATE outreach_messages SET body=? WHERE id=?", (body, mid))
        conn.commit()
        return ""


CSS = """body{font-family:system-ui,sans-serif;background:#f4f5f7;margin:0;color:#1a1a1a}
.bar{position:sticky;top:0;z-index:5;background:#111;color:#fff;padding:10px 18px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.bar a{color:#9ecbff;text-decoration:none;font-size:13px}
.wrap{max-width:880px;margin:16px auto;padding:0 14px 60px}
.sec{background:#fff;border:1px solid #e1e3e6;border-radius:10px;padding:12px 14px;margin-bottom:12px}
.sec h2{margin:0 0 8px;font-size:15px}
.note{background:#fffbe6;border:1px solid #e6c200;border-radius:8px;padding:8px 12px;font-size:13px;margin-bottom:12px}
.err{background:#fdecea;border:1px solid #e57373;border-radius:8px;padding:8px 12px;font-size:13px;margin-bottom:12px}
.ok{background:#e6f4ea;border:1px solid #34a853;border-radius:8px;padding:8px 12px;font-size:13px;margin-bottom:12px}
.card{background:#fff;border:1px solid #e1e3e6;border-radius:10px;padding:12px 14px;margin-bottom:12px}
.meta{font-size:12px;color:#666;display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.pill{border-radius:20px;padding:1px 9px;font-size:12px;font-weight:600}
.QUEUED{background:#fef7e0}.APPROVED{background:#e6f4ea}.SENT{background:#e8eaed;color:#555}.FAILED{background:#fce8e6}.SKIPPED{background:#f1f1f1;color:#888}
input[type=text],select,textarea{border:1px solid #ccc;border-radius:6px;padding:7px;font-size:13px;font-family:inherit;box-sizing:border-box}
textarea{width:100%;min-height:110px;resize:vertical;margin-top:6px}
.row{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;align-items:center}
button,.btn{border:1px solid #ccc;background:#f8f9fa;border-radius:6px;padding:5px 12px;font-size:13px;cursor:pointer;text-decoration:none;color:#1a1a1a}
button.primary{background:#1a73e8;color:#fff;border-color:#1a73e8}
button.send{background:#188038;color:#fff;border-color:#188038}
a.wa{background:#25d366;color:#fff;border:1px solid #25d366;border-radius:6px;padding:5px 12px;font-size:13px;text-decoration:none}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}@media(max-width:640px){.grid{grid-template-columns:1fr}}
label{font-size:12px;color:#555;display:block;margin-top:6px}label input,label textarea{margin-top:3px}
pre{white-space:pre-wrap;font-size:12px;color:#a00;margin:6px 0 0}
h3{margin:0 0 2px;font-size:15px}.topline{display:flex;justify-content:space-between;align-items:center;gap:8px}
.search{width:100%;margin-bottom:8px}.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px}
"""


def _esc(s) -> str:
    return html.escape(s or "")


def _queue_cards(msgs) -> str:
    out = []
    for m in msgs:
        to = m["email"] or m["phone"] or "(no contact)"
        subj = (f"<input type='text' style='width:100%' name='subject' value='{_esc(m['subject'])}'>"
                if m["channel"] == "EMAIL" else "")
        btns = ["<button name='op' value='save'>Save edit</button>",
                "<button name='op' value='regen' title='Rebuild from profile'>Regen</button>"]
        if m["status"] == "QUEUED":
            btns.append("<button name='op' value='approve'>Approve</button>")
        if m["channel"] == "EMAIL" and m["status"] == "APPROVED":
            btns.append("<button class='send' name='op' value='send'>Send email</button>")
        if m["channel"] == "WHATSAPP":
            if m["link"]:
                btns.append(f"<a class='wa' target='_blank' href='{m['link']}'>Open WhatsApp</a>")
            if m["status"] in ("QUEUED", "APPROVED"):
                btns.append("<button name='op' value='approve'>Approve</button>")
                btns.append("<button name='op' value='wa_sent'>Mark sent</button>")
        btns += ["<button name='op' value='skip'>Skip</button>", "<button name='op' value='block'>Block</button>"]
        out.append(
            f"<div class='card'><div class='topline'><h3>#{m['id']} {_esc(m['co'])} — {_esc(m['job'])}</h3>"
            f"<span class='pill {m['status']}'>{m['status']}</span></div>"
            f"<div class='meta'><span>{m['channel']}</span><span>{_esc(to)}</span>"
            f"<span>{_esc((m['error'] or '')[:120])}</span></div>"
            f"<form method='post'><input type='hidden' name='id' value='{m['id']}'>{subj}"
            f"<textarea name='body'>{_esc(m['body'])}</textarea>"
            f"<div class='row'>{' '.join(btns)}</div></form></div>")
    return "".join(out) or "<div class='card'>Nothing matches. Run a sync or clear search.</div>"


def _profile_form(p: dict) -> str:
    fields = []
    for k in ("name", "title", "email", "phone", "location", "portfolio", "github", "linkedin"):
        fields.append(f"<label>{k}<input type='text' style='width:100%' name='{k}' value='{_esc(p.get(k, ''))}'></label>")
    fields.append(f"<label>skills<textarea name='skills' style='min-height:44px'>{_esc(p.get('skills', ''))}</textarea></label>")
    fields.append(f"<label>summary<textarea name='summary' style='min-height:60px'>{_esc(p.get('summary', ''))}</textarea></label>")
    return ("<form method='post'><div class='grid'>" + "".join(fields) + "</div>"
            "<div class='row'><button class='primary' name='op' value='profile_save'>Save profile</button>"
            "<span style='font-size:12px;color:#666'>Used for new messages + Regen. Old messages update only via Regen.</span></div></form>")


def _page(qs: dict) -> bytes:
    filt = (qs.get("f", ["QUEUED"])[0] if isinstance(qs.get("f"), list) else qs.get("f", "QUEUED")).upper()
    ch = (qs.get("ch", ["ALL"])[0] if isinstance(qs.get("ch"), list) else qs.get("ch", "ALL")).upper()
    sort = (qs.get("sort", ["new"])[0] if isinstance(qs.get("sort"), list) else qs.get("sort", "new")).lower()
    q = (qs.get("q", [""])[0] if isinstance(qs.get("q"), list) else qs.get("q", "")).strip().lower()
    with get_db() as conn:
        counts = {r["status"]: r["c"] for r in
                  conn.execute("SELECT status, COUNT(*) c FROM outreach_messages GROUP BY status").fetchall()}
        counts["ALL"] = sum(counts.values())
        n_apps = conn.execute("SELECT COUNT(*) c FROM indeed_applications").fetchone()["c"]
        n_co = conn.execute("SELECT COUNT(*) c FROM companies").fetchone()["c"]
        rows = [dict(r) for r in conn.execute(
            "SELECT m.*, c.email, c.phone, co.name co, a.job_title job FROM outreach_messages m "
            "LEFT JOIN contacts c ON c.id=m.contact_id LEFT JOIN companies co ON co.id=m.company_id "
            "LEFT JOIN indeed_applications a ON a.id=m.application_id ORDER BY m.id DESC LIMIT 500").fetchall()]
    if filt != "ALL":
        rows = [r for r in rows if r["status"] == filt]
    if ch != "ALL":
        rows = [r for r in rows if r["channel"] == ch]
    if q:
        rows = [r for r in rows if q in " ".join(
            str(r[k] or "") for k in ("co", "job", "email", "phone", "subject", "body")).lower()]
    if sort == "old":
        rows.sort(key=lambda r: r["id"])
    elif sort == "co":
        rows.sort(key=lambda r: (r["co"] or "").lower())
    for m in rows:
        m["link"] = wa_link(m["phone"] or "", m["body"] or "") if m["channel"] == "WHATSAPP" else ""
    dry = _live("DRY_RUN", "1") == "1"
    smtp_ok = bool(_live("SMTP_HOST") and _live("SMTP_USERNAME"))
    p = load_profile()
    flash = f"<div class='{'err' if FLASH['err'] else 'ok'}'>{_esc(FLASH['msg'])}</div>" if FLASH["msg"] else ""
    send_note = ("" if (not dry and smtp_ok) else
                 "<div class='note'>Email Send is OFF (DRY_RUN=1 or no SMTP). Edit + approve works; set .env to enable Send.</div>")
    tabs = " ".join(f"<a href='/?f={f}&ch={ch}&sort={sort}&q={_esc(q)}'>{f} ({counts.get(f, 0)})</a>"
                    for f in ("QUEUED", "APPROVED", "SENT", "ALL"))
    return (f"<html><head><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Outreach</title><style>{CSS}</style></head><body>"
            f"<div class='bar'><b>Outreach</b>{tabs}"
            f"<span style='margin-left:auto;font-size:12px'>{'DRY_RUN=1' if dry else 'LIVE'} · "
            f"<a href='#controls'>Sync</a> · <a href='#queue'>Queue</a> · <a href='#profile'>Profile</a></span></div>"
            f"<div class='wrap'>{flash}"
            f"<div class='sec' id='controls'><h2>Sync · {n_apps} applications · {n_co} companies · {counts.get('QUEUED', 0)} queued</h2>"
            f"<form method='post'><div class='row'>"
            f"<button class='primary' name='op' value='sync'>Sync now (live)</button>"
            f"<button name='op' value='sync_offline'>Sync offline</button>"
            f"</div></form></div>"
            f"<div class='sec' id='queue'><h2>Queue</h2>"
            f"<form method='get'><input class='search' type='text' name='q' placeholder='Search company, job, email, text…' value='{_esc(q)}'>"
            f"<div class='filters'><select name='f'>"
            + "".join(f"<option value='{f}'{' selected' if filt == f else ''}>{f}</option>" for f in ("QUEUED", "APPROVED", "SENT", "FAILED", "SKIPPED", "ALL"))
            + f"</select><select name='ch'>"
            + "".join(f"<option value='{c}'{' selected' if ch == c else ''}>{c}</option>" for c in ("ALL", "EMAIL", "WHATSAPP"))
            + f"</select><select name='sort'>"
            + "".join(f"<option value='{s}'{' selected' if sort == s else ''}>{l}</option>" for s, l in (("new", "Newest"), ("old", "Oldest"), ("co", "Company A–Z")))
            + f"</select><button>Apply</button><span style='color:#666'>{len(rows)} shown</span></div></form></div>"
            f"{send_note}{_queue_cards(rows)}"
            f"<div class='sec' id='profile'><h2>My details (used in messages)</h2>{_profile_form(p)}"
            f"<div style='font-size:12px;color:#666;margin-top:6px'>Resume: {_esc(str(config.RESUME_PATH))} — attached to emails.</div></div>"
            f"</div></body></html>").encode()


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        init_db()
        self._send(_page(parse_qs(urlparse(self.path).query)))

    def do_POST(self):
        init_db()
        n = int(self.headers.get("Content-Length", 0))
        f = parse_qs(self.rfile.read(n).decode())
        g = lambda k, d="": (f.get(k) or [d])[0]
        op, mid = g("op"), int(g("id", "0") or 0)
        msg, err = "", False
        try:
            if op == "save":
                with get_db() as conn:
                    if "subject" in f:
                        conn.execute("UPDATE outreach_messages SET subject=?, body=? WHERE id=?", (g("subject"), g("body"), mid))
                    else:
                        conn.execute("UPDATE outreach_messages SET body=? WHERE id=?", (g("body"), mid))
                    conn.commit()
                msg = f"#{mid} saved."
            elif op == "regen":
                e = _regen(mid)
                msg, err = ((f"#{mid} rebuilt from profile.", False) if not e else (f"#{mid}: {e}", True))
            elif op in ("approve", "skip"):
                with get_db() as conn:
                    conn.execute("UPDATE outreach_messages SET status=? WHERE id=?",
                                 ("APPROVED" if op == "approve" else "SKIPPED", mid))
                    conn.commit()
                msg = f"#{mid} {op}d."
            elif op == "block":
                with get_db() as conn:
                    m = conn.execute("SELECT c.email, c.phone FROM outreach_messages m LEFT JOIN contacts c "
                                     "ON c.id=m.contact_id WHERE m.id=?", (mid,)).fetchone()
                    if m:
                        conn.execute("INSERT INTO suppression_list(email,phone,reason) VALUES(?,?,'dashboard block')",
                                     (m["email"] or "", m["phone"] or ""))
                    conn.execute("UPDATE outreach_messages SET status='SKIPPED' WHERE id=?", (mid,))
                    conn.commit()
                msg = f"#{mid} blocked."
            elif op == "wa_sent":
                with get_db() as conn:
                    conn.execute("UPDATE outreach_messages SET status='SENT', sent_at=datetime('now') WHERE id=?", (mid,))
                    conn.commit()
                msg = f"#{mid} marked sent."
            elif op == "send":
                e = _send_email(mid)
                msg, err = ((f"#{mid} sent.", False) if not e else (f"#{mid}: {e}", True))
            elif op == "profile_save":
                save_profile({k: g(k) for k in DEFAULT_PROFILE})
                msg = "Profile saved. New messages + Regen use it."
            elif op in ("sync", "sync_offline"):
                from app.scheduler import run_cycle
                r = run_cycle(offline=(op == "sync_offline"), enrich=True)
                msg = f"Sync done: {r.get('new_apps', 0)} new apps, {r.get('queued_emails', 0)} emails + {r.get('queued_whatsapp', 0)} WA queued."
        except Exception as e:  # noqa: BLE001 — surfaced in UI
            msg, err = str(e)[:300], True
        FLASH["msg"], FLASH["err"] = msg, err
        self.send_response(303)
        self.send_header("Location", "/?f=QUEUED" if op in ("approve", "skip") else "/")
        self.end_headers()

    def _send(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def serve(port: int | None = None):
    HTTPServer(("127.0.0.1", port or int(_live("DASHBOARD_PORT", "8787") or 8787)), H).serve_forever()


if __name__ == "__main__":
    serve()
