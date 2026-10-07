"""Grab Indeed session cookie from YOUR live logged-in Chrome. Never prints/logs the cookie.

Strategy: attach to your running Chrome via remote debugging (no re-login, no second
profile). Falls back to a dedicated window only if Chrome wasn't started with the flag.
"""
from __future__ import annotations
from app import config

PROFILE_DIR = config.DATA_DIR / "chrome-profile"
LOGIN_URL = "https://myjobs.indeed.com/applied"
CDP_PORT = 9222

CHROME_FLAG_CMD = (
    "Live Chrome not reachable. Fix, no Chrome-killing needed:\n"
    '  Option 1 (easiest): python run.py indeed-login --fresh\n'
    '  Option 2: double-click chrome-debug.bat, log in to Indeed in the opened window,\n'
    "  then re-run: python run.py indeed-login"
)

def save_cookie_to_env(cookie: str, tk: str = "") -> None:
    env = config.BASE_DIR / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    lines = [l for l in lines if not l.startswith("INDEED_COOKIE=")]
    lines.append(f"INDEED_COOKIE={cookie}")
    if tk:  # never wipe a previously captured tk with empty
        lines = [l for l in lines if not l.startswith("INDEED_TK=")]
        lines.append(f"INDEED_TK={tk}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _jar(raw: list[dict]) -> tuple[str, int]:
    seen: dict[str, str] = {}
    for c in raw:
        if c.get("domain", "").endswith("indeed.com"):
            seen[c["name"]] = c["value"]
    return "; ".join(f"{k}={v}" for k, v in seen.items()), len(seen)

def _find_tk(raw: list[dict]) -> str:
    # ponytail: best-effort only; feed works without tk (client sends it only if set)
    for c in raw:
        if c.get("name", "").lower() == "tk":
            return c["value"]
    return ""

def verify_cookie(cookie: str) -> bool:
    """One cheap feed request. True unless Indeed says 401. Never logs the cookie."""
    import requests
    try:
        r = requests.get(config.INDEED_URL,
            params={"type": "POST_APPLY", "applyUpdateStartTime": "0", "from": "app-tracker"},
            headers={"Accept": "application/json", "Cookie": cookie}, timeout=20)
        return r.status_code != 401
    except Exception:
        return False

def login_via_live_browser(port: int = CDP_PORT) -> int:
    """Attach to your already-running Chrome. Never closes it."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("playwright missing. Run: pip install playwright")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception:
            raise RuntimeError(f"Live Chrome not reachable.\n{CHROME_FLAG_CMD}")
        raw: list[dict] = []
        for ctx in browser.contexts:
            raw.extend(ctx.cookies())
        # ponytail: no browser.close() — that would kill the user's Chrome; dropping the CDP link is enough
    jar, n = _jar(raw)
    if not jar:
        raise RuntimeError("Attached to Chrome, but no Indeed cookies. Open indeed.com in it first, then re-run.")
    tk = _find_tk(raw)
    save_cookie_to_env(jar, tk)
    print(f"tk: {'captured' if tk else 'not found (optional, continuing without it)'}")
    if not verify_cookie(jar):
        raise RuntimeError("Cookie saved, but Indeed rejected it (401). Log in to Indeed in that Chrome window, then re-run.")
    print("cookie verified against Indeed feed.")
    return n

def login_via_fresh_window() -> int:
    from playwright.sync_api import sync_playwright
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR), channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        try:
            input("Log in to Indeed in the opened Chrome window if asked, then press Enter here... ")
        except KeyboardInterrupt:
            raise SystemExit("cancelled.")
        raw = ctx.cookies()
        ctx.close()
    jar, n = _jar(raw)
    if not jar:
        raise RuntimeError("No Indeed cookies found. Complete the login, then press Enter.")
    save_cookie_to_env(jar, _find_tk(raw))
    return n

def login_and_save_cookie(fresh: bool = False) -> int:
    if fresh:
        return login_via_fresh_window()
    try:
        return login_via_live_browser()
    except RuntimeError as e:
        # ponytail: no silent fallback window — user rejected re-login; point at the .bat instead
        raise SystemExit(f"{e}\nTip: double-click chrome-debug.bat, then re-run this command.")
