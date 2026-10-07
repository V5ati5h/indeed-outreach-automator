"""Public-business-contact enrichment only. Never guess personal mobiles."""
from __future__ import annotations
import re, sqlite3, urllib.request

ROLE_PRIORITY = ("careers@", "hr@", "recruitment@", "talent@", "jobs@")
EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)
PHONE_RE = re.compile(r"\+?91[\s-]?\d{5}[\s-]?\d{5}|\b\d{10}\b")

def classify_email(e: str) -> tuple[str, str]:
    local = e.split("@")[0].lower()
    if local in ("careers", "hr", "recruitment", "talent", "jobs"):
        return "PUBLIC_HR_EMAIL", "HIGH"
    if local in ("info", "contact", "hello", "support", "admin"):
        return "PUBLIC_COMPANY_EMAIL", "MEDIUM"
    return "PUBLIC_COMPANY_EMAIL", "LOW"

def scrape_public_contacts(url: str, timeout: int = 15) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    except Exception:
        return {"emails": [], "phones": []}
    return {"emails": sorted(set(EMAIL_RE.findall(html)))[:10],
            "phones": sorted(set(p.strip() for p in PHONE_RE.findall(html)))[:10]}

def save_contact(conn: sqlite3.Connection, company_id: int, email: str = "", phone: str = "",
                  name: str = "", source: str = "", role: str = "") -> None:
    if role == "":
        role, conf = classify_email(email) if email else ("PUBLIC_COMPANY_PHONE" if phone else "UNKNOWN", "MEDIUM" if phone else "LOW")
    else:
        conf = "HIGH" if role == "PUBLIC_HR_EMAIL" else "MEDIUM"
    if not email and not phone:
        return
    conn.execute("""INSERT OR IGNORE INTO contacts(company_id,name,email,phone,role,source,confidence)
     VALUES(?,?,?,?,?,?,?)""", (company_id, name, email, phone, role, source, conf))

def enrich_company(conn: sqlite3.Connection, company_id: int) -> int:
    """Scrape website + careers_url if present. Returns contacts added."""
    row = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    if not row:
        return 0
    before = conn.execute("SELECT COUNT(*) c FROM contacts WHERE company_id=?", (company_id,)).fetchone()["c"]
    for url in [u for u in (row["website"], row["careers_url"]) if u]:
        found = scrape_public_contacts(url)
        for e in found["emails"]:
            role, _ = classify_email(e)
            save_contact(conn, company_id, email=e, source=url, role=role)
        for p in found["phones"]:
            save_contact(conn, company_id, phone=p, source=url, role="PUBLIC_COMPANY_PHONE")
    conn.commit()
    after = conn.execute("SELECT COUNT(*) c FROM contacts WHERE company_id=?", (company_id,)).fetchone()["c"]
    return after - before
