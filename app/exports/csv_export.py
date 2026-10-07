"""CSV export (job_leads.csv stays an export, DB is source of truth)."""
from __future__ import annotations
import csv, sqlite3

HEADERS = ["Lead ID", "Lead Name", "Company", "Email", "Phone", "Website", "Contact Type",
 "Location", "Careers URL", "Target Roles", "Lead Priority", "Source URL",
 "Indeed Jobs Count", "Indeed Job Titles", "Indeed Locations", "Indeed Candidate Status",
 "Indeed Employer Status", "Indeed Active Openings"]

def export_csv(conn: sqlite3.Connection, path: str) -> int:
    rows = conn.execute("""SELECT co.id, co.name, co.website, co.location, co.careers_url,
      ct.name cname, ct.email, ct.phone, ct.role,
      (SELECT COUNT(*) FROM indeed_applications a WHERE a.company_id=co.id) jc
     FROM companies co LEFT JOIN contacts ct ON ct.company_id=co.id
     GROUP BY co.id""").fetchall()
    apps = {}
    for a in conn.execute("SELECT * FROM indeed_applications"):
        apps.setdefault(a["company_id"], []).append(a)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        for i, r in enumerate(rows, 1):
            al = apps.get(r["id"], [])
            w.writerow({
                "Lead ID": f"TS-{i:04d}", "Lead Name": r["cname"] or "Indeed Application Contact",
                "Company": r["name"], "Email": r["email"] or "", "Phone": r["phone"] or "",
                "Website": r["website"] or "", "Contact Type": r["role"] or "Indeed application lead",
                "Location": r["location"] or "", "Careers URL": r["careers_url"] or "",
                "Target Roles": " | ".join(x["job_title"] for x in al),
                "Lead Priority": "A", "Source URL": (al[0]["job_url"] if al else ""),
                "Indeed Jobs Count": len(al),
                "Indeed Job Titles": " | ".join(x["job_title"] for x in al),
                "Indeed Locations": " | ".join(x["location"] for x in al),
                "Indeed Candidate Status": " | ".join(x["candidate_status"] for x in al),
                "Indeed Employer Status": " | ".join(x["employer_status"] for x in al),
                "Indeed Active Openings": sum(1 for x in al if x["employer_status"] == "OPEN")})
    return len(rows)
