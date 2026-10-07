# Indeed Outreach Automator

Turns your Indeed job applications into an organized, approval-gated outreach pipeline.

**What it does:** collects your Indeed applications + your `job_leads.csv` → stores them in SQLite → finds public business contacts → scores each lead (A/B/C/HOLD) → drafts personalized emails + WhatsApp messages → you approve → it sends (email) or opens click-to-chat (WhatsApp) → logs everything, handles opt-outs and follow-ups.

**What it does NOT do:** no unattended bulk messaging, no scraping personal phone numbers, no auto-sending WhatsApp spam. Every send passes a human approval gate. See [Compliance](#compliance--safety-rules).

---

## 1. Prerequisites

- Python 3.10+ (`python --version`)
- Your Indeed account (logged in, in your own browser)
- An SMTP mailbox for sending emails (Gmail App Password / Outlook / any provider)
- Your resume PDF

## 2. Setup (first time, ~10 min)

```bat
cd indeed-outreach-automator

:: 1. Install dependencies
pip install -r requirements.txt

:: 2. Create your secrets file (never commit this)
copy .env.example .env
```

**3. Fill in `.env`:**

| Variable                                | Where to get it                                                                  |
| --------------------------------------- | -------------------------------------------------------------------------------- |
| `INDEED_COOKIE`                         | Auto-filled by `python run.py indeed-login` (opens your Chrome, log in once) — or paste manually from DevTools |
| `INDEED_TK`                             | Same request's`tk` query param (optional)                                        |
| `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM` | Your mail provider's SMTP settings                                               |

**4. Add your resume:**

```
assets/Satish_Vishwakarma_Resume.pdf
```

(A temporary placeholder is already there — replace it with the real one before real outreach.)

**5. Initialize + load your existing data:**

```bat
python run.py init        :: creates data/outreach.db
python run.py migrate     :: imports assets/job_leads.csv (~135 companies, safe to re-run)
```

## 3. Running

**Just run it (auto-sequence: init → ingest CSV → refresh cookie → sync):**

```bat
python run.py
```

**Indeed login (cookie auto-grab) — only if auto says no cookie, re-run whenever sync gets a 401:**

```bat
python run.py indeed-login
:: needs YOUR live Chrome once: double-click chrome-debug.bat (relaunches same profile, stays logged in)
:: then re-run — attaches to it, saves cookie to .env. No re-login, ever.
:: (fallback: --fresh opens a separate window where you log in manually)
```

**Daily loop — one command does a full cycle:**

```bat
python run.py sync
```

Each cycle: ingest `job_leads.csv` → fetch Indeed feed → upsert applications → enrich public contacts → score leads → queue drafts → regenerate `exports/job_leads.csv` → write audit log to `logs/<timestamp>_sync.json`.

**Offline mode** (no Indeed request — uses a saved `indeed_applications.json`):

```bat
python run.py sync --offline
python run.py sync --offline --no-enrich    :: skip website scraping, fastest
```

**Review + approve queue (dashboard):**

```bat
python run.py dashboard
:: open http://127.0.0.1:8787 → Approve / Skip / Block per message
```

**Send an approved email** (works only with `DRY_RUN=0` in `.env`):

```bat
python run.py send-approved --msg 3
```

**WhatsApp:** the dashboard gives you a `wa.me` click-to-chat link per approved message — you send from WhatsApp yourself. No automation.

## 4. Automate it (every 2 hours)

- **Windows Task Scheduler:** action `python C:\Users\V5ati5h\Github\indeed-outreach-automator\run.py sync`, trigger every 2h.
- **cron (Linux/VPS):** `0 */2 * * * cd /path/to/AutoCold && python run.py sync >> logs/cron.log 2>&1`

## 5. How leads are scored

| Signal                                         |         Points |
| ---------------------------------------------- | -------------: |
| Job still OPEN                                 |            +30 |
| Applied recently                               |            +20 |
| Role matches your services                     |            +20 |
| Public HR email / named contact / public phone | +15 / +10 / +5 |
| Already queued or sent                         |            −80 |
| Rejected / withdrawn → blocked; closed job     |            −50 |
| Opted out (suppression list)                   |      hard HOLD |

`≥80 → A`, `60–79 → B`, `40–59 → C`, `<40 → HOLD` (never queued).

Follow-ups: `MAX_FOLLOWUPS=2`, `FOLLOWUP_DELAY_DAYS=5` in `.env`. A reply stops the sequence. **Block** in the dashboard (or any opt-out) adds the contact to `suppression_list` — it can never re-enter the queue.

## 6. Project structure

```
run.py                        :: CLI entry: init | migrate | sync | dashboard | send-approved
app/config.py                 :: all settings from .env (secrets never logged)
app/database.py               :: SQLite schema (companies, contacts, applications, messages, suppression, sync_runs)
app/indeed/                   :: client.py (feed fetch) / parser.py (normalize) / sync.py (upsert)
app/enrichment/contacts.py    :: public business contacts only, with source + confidence
app/outreach/                 :: scorer.py / templates.py / email_sender.py / whatsapp.py / suppression.py
app/exports/                  :: migrate.py (CSV ingest) / csv_export.py (CSV export)
app/scheduler.py              :: the full cycle
dashboard/app.py              :: approval queue UI (stdlib only, zero deps)
assets/                       :: inputs — your resume PDF + master job_leads.csv
data/outreach.db              :: the database (git-ignored, rebuild anytime)
exports/job_leads.csv         :: generated export (git-ignored)
logs/                         :: per-run audit JSON (git-ignored)
assets/job_leads.csv          :: your master lead list — a live input, re-ingested every sync
```

## 7. Compliance & safety rules

- **Approval gate:** `DRY_RUN=1` is the default — nothing sends until you approve in the dashboard and set `DRY_RUN=0`.
- **WhatsApp is manual-only.** Drafts + `wa.me` links only. No OpenWA / whatsapp-web.js bulk automation (bannable, against WhatsApp terms).
- **Public data only.** Company websites / careers pages. Contacts are tagged `PUBLIC_HR_EMAIL`, `PUBLIC_COMPANY_PHONE`, etc. with source + confidence. Personal numbers are never guessed.
- **Secrets:** `INDEED_COOKIE` lives in `.env` only — never in code, DB, or logs. `.gitignore` already excludes `.env`, the DB, and logs.
- Respect Indeed's terms, WhatsApp's terms, your SMTP provider's policies, and applicable anti-spam/privacy laws.

## 8. Troubleshooting

| Symptom                   | Fix                                                                             |
| ------------------------- | ------------------------------------------------------------------------------- |
| `INDEED_COOKIE missing`   | Copy fresh Cookie header from your browser DevTools into`.env` (cookies expire) |
| `SMTP not configured`     | Fill`SMTP_HOST/USERNAME/FROM` in `.env`; keep `DRY_RUN=1` until tested          |
| `DRY_RUN=1: approve…`     | Expected — approve in dashboard, set`DRY_RUN=0` only for real sends             |
| No contacts for a company | Add its`website`/`careers_url` to the DB or CSV, re-run `sync`                  |
| Start over                | Delete`data/outreach.db`, re-run `init` + `migrate` + `sync`                    |
