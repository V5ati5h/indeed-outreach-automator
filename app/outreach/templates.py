"""Jobseeker templates. First-person applicant tone. No agency/outsourcing claims."""
from __future__ import annotations
import json
from app import config

PROFILE_PATH = config.DATA_DIR / "profile.json"

DEFAULT_PROFILE = {
    "name": "Satish Vishwakarma",
    "title": "Full-Stack Developer",
    "email": "",
    "phone": "",
    "location": "India",
    "skills": "Laravel/PHP, WordPress, Python, MySQL, REST APIs",
    "portfolio": "",
    "github": "",
    "linkedin": "",
    "summary": "Full-stack developer working with Laravel/PHP, WordPress, backend systems and Python.",
}


def load_profile() -> dict:
    try:
        if PROFILE_PATH.exists():
            d = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_PROFILE, **{k: v for k, v in d.items() if k in DEFAULT_PROFILE}}
    except (OSError, ValueError):
        pass
    return dict(DEFAULT_PROFILE)


def save_profile(data: dict) -> dict:
    p = {k: str(data.get(k, DEFAULT_PROFILE[k])).strip() for k in DEFAULT_PROFILE}
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(p, indent=2), encoding="utf-8")
    return p


def first_name(name: str, email: str = "") -> str:
    if name and name.lower() not in ("indeed application contact", "hr / recruitment team"):
        return name.split()[0]
    local = email.split("@")[0] if "@" in email else ""
    return "" if local.lower() in ("hr", "info", "sales", "hello", "connect", "contact", "admin", "careers") else local


def _sig(p: dict) -> str:
    lines = [p["name"], p["title"] if p["title"] else ""]
    if p["skills"]:
        lines.append(p["skills"])
    contact = " | ".join(x for x in (p["email"], p["phone"]) if x)
    if contact:
        lines.append(contact)
    links = " | ".join(x for x in (p["portfolio"], p["github"], p["linkedin"]) if x)
    if links:
        lines.append(links)
    if p["location"]:
        lines.append(p["location"])
    return "\n".join(x for x in lines if x)


def email_subject(job_title: str) -> str:
    return f"Application for {job_title or 'Developer Role'} — {load_profile()['name']}"


def email_body(name: str, company: str, role: str, location: str, job_url: str = "") -> str:
    p = load_profile()
    g = f"Hi {name}," if name else "Hi there,"
    where = f" at {company}" if company else ""
    loc = f" in {location}" if location else ""
    ref = f"\nJob reference: {job_url}" if job_url else ""
    return (f"{g}\n\nI recently applied for the {role or 'developer role'}{where}{loc}, "
            f"and wanted to personally share my profile.\n\n"
            f"I'm {p['name']}"
            f"{(', ' + p['title']) if p['title'] else ''}"
            f"{('. ' + p['summary']) if p['summary'] else '.'}\n"
            f"{('Key skills: ' + p['skills'] + '\n') if p['skills'] else ''}"
            f"{ref}\nI've attached my resume for your review. "
            f"I'd welcome a brief conversation about the role.\n\nThank you for your time.\n\n{_sig(p)}").strip()


def whatsapp_body(name: str, company: str, role: str, location: str) -> str:
    p = load_profile()
    g = f"Hi {name}," if name else "Hi there,"
    where = f" at {company}" if company else ""
    loc = f" in {location}" if location else ""
    return (f"{g}\n\nI recently applied for the {role or 'developer role'}{where}{loc} "
            f"and wanted to share my profile.\n\nI'm {p['name']}"
            f"{(', ' + p['title']) if p['title'] else ''}"
            f"{(' — ' + p['skills']) if p['skills'] else ''}.\n\n"
            f"Happy to share my resume and discuss. Thank you!").strip()


def wa_link(phone: str, msg: str) -> str:
    import re, urllib.parse
    d = re.sub(r"\D", "", phone or "")
    if d.startswith("91") and len(d) == 12: d = d
    elif len(d) == 10: d = "91" + d
    return f"https://wa.me/{d}?text={urllib.parse.quote(msg)}" if d else ""
