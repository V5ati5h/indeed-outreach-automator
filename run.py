"""run.py: sync | migrate | dashboard | send-approved. DRAFT/APPROVAL-GATED by default."""
from __future__ import annotations
import argparse
from app.database import init_db, get_db
from app.scheduler import run_cycle, LEGACY_CSV
from app.exports.migrate import migrate

def do_auto(offline: bool, enrich: bool) -> None:
    """Bare `python run.py`: fresh/deleted state heals itself, then full cycle."""
    from app import config
    init_db()
    if LEGACY_CSV.exists():
        with get_db() as c:
            print({"csv_ingest": migrate(c, str(LEGACY_CSV))})
    else:
        print(f"leads csv missing: {LEGACY_CSV}")
    use_offline = offline
    if not use_offline and not config.INDEED_COOKIE:
        try:
            from app.indeed.browser import login_via_live_browser
            print(f"cookie auto-refreshed ({login_via_live_browser()} cookies).")
            for line in (config.BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
                if line.startswith("INDEED_COOKIE="):
                    config.INDEED_COOKIE = line.split("=", 1)[1]
        except Exception as e:
            print(f"auto-login skipped: {e}")
    if not use_offline and not config.INDEED_COOKIE:
        if (config.BASE_DIR / "indeed_applications.json").exists():
            print("no cookie — falling back to offline fixture.")
            use_offline = True
        else:
            raise SystemExit("no INDEED_COOKIE and no offline fixture. Double-click chrome-debug.bat, then run: python run.py indeed-login")
    print(run_cycle(offline=use_offline, enrich=enrich))

def main():
    p = argparse.ArgumentParser(description="Indeed -> DB -> queue -> gated send (no args = full auto sequence)")
    p.add_argument("cmd", nargs="?", default="auto",
                   choices=["auto", "sync", "migrate", "dashboard", "send-approved", "init", "indeed-login"])
    p.add_argument("--offline", action="store_true", help="use indeed_applications.json")
    p.add_argument("--no-enrich", action="store_true")
    p.add_argument("--msg", type=int, default=0)
    p.add_argument("--fresh", action="store_true", help="indeed-login: use separate window instead of live Chrome")
    a = p.parse_args()
    if a.cmd == "auto":
        do_auto(a.offline, not a.no_enrich)
    elif a.cmd == "init":
        print(init_db())
    elif a.cmd == "migrate":
        init_db()
        with get_db() as c:
            print(migrate(c, str(LEGACY_CSV)))
    elif a.cmd == "sync":
        print(run_cycle(offline=a.offline, enrich=not a.no_enrich))
    elif a.cmd == "dashboard":
        from dashboard.app import serve
        print("http://127.0.0.1:8787")
        serve()
    elif a.cmd == "send-approved":
        from app.outreach import send_approved
        print("sent:", send_approved(a.msg))
    elif a.cmd == "indeed-login":
        from app.indeed.browser import login_and_save_cookie
        try:
            print("indeed cookies saved:", login_and_save_cookie(fresh=a.fresh))
        except KeyboardInterrupt:
            print("cancelled.")

if __name__ == "__main__":
    main()
