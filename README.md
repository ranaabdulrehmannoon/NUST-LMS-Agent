
# NUST LMS Agent (Local Agent)

Local-only agent that logs into the official NUST Moodle LMS with your credentials, monitors selected courses for new uploads and assignment deadlines, and emails you notifications via **SMTP**. Runs once per invocation (Task Scheduler/Cron-friendly). You keep your credentials locally; nothing is sent anywhere else.

## Features
- Playwright-based login/session (handles cookies/CSRF via real browser).
- Course filtering via env var.
- Detects new file resources per course (tracked in SQLite).
- Tracks assignments, due dates, and submitted status heuristics.
- Reminder thresholds: overdue, 72h, 48h, 24h before due.
- SMTP email notifications with de-duplication stored in SQLite.
- Single-shot run for use with schedulers.

## Prerequisites
- Python 3.10+ (virtualenv recommended).
- Playwright Chromium binaries installed (`python -m playwright install chromium`). Already fetched in this workspace; you can re-run if needed.

## Setup

### Step 1: LMS Configuration
1) Create your env file:
```
copy .env.example .env
```
Fill in values:
- `LMS_BASE_URL`: e.g., `https://lms.nust.edu.pk/portal/`
- `LMS_USERNAME`, `LMS_PASSWORD`: your credentials (kept locally).
- `COURSE_FILTER`: comma-separated course ids or names to monitor; leave empty to monitor all enrolled courses.
- `HEADLESS=true` for silent runs; `false` for debugging.

### Step 2: SMTP Email Setup
**For Gmail:**
1. Enable 2-factor authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Create a new app password for "Mail"
4. Use that password in `.env` as `SMTP_PASSWORD`

Update `.env` with:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_16_digit_app_password
SMTP_FROM=your_email@gmail.com
SMTP_TO=recipient@gmail.com
```

### Step 3: Install Dependencies
```
pip install -r requirements.txt
python -m playwright install chromium
```

## Running

The program runs **continuously** in the background, checking for updates at regular intervals defined by `CHECK_INTERVAL_MINUTES` in your `.env` file.

### Starting the Program
```bash
python lms_agent/runner.py
```

The agent will:
- Run continuously, checking every `CHECK_INTERVAL_MINUTES` (default: 60 minutes)
- Log in, fetch enrolled courses, filter per `COURSE_FILTER`
- Scrape files/assignments; record new items into `lms_agent.db`
- Send emails for new files and for due-date thresholds/overdue assignments
- Automatically wait for the configured interval before checking again

### Stopping the Program
- Press **Ctrl+C** in the terminal to gracefully stop the agent
- The program will finish its current check and then exit

### Running Options
```bash
# Run continuously (recommended)
python lms_agent/runner.py

# Run once and exit (for Task Scheduler/Cron)
python -c "from lms_agent.runner import run_once; run_once()"
```

## Scheduling (Alternative to Continuous Running)
If you prefer scheduled runs instead of continuous operation:
- **Windows Task Scheduler**: create a task to run `python -c "from lms_agent.runner import run_once; run_once()"` every hour. Use `Start in` = repo directory so `lms_agent.db` is found.
- **Cron (WSL/Linux)**: `0 * * * * cd /path/to/repo && /usr/bin/python -c "from lms_agent.runner import run_once; run_once()"`

## Important Notes
- Selectors are set for standard Moodle/Boost themes. If your LMS theme differs, adjust selectors in `lms_agent/fetcher.py` (file resources and assignments).
- No CAPTCHA bypass is attempted. If your LMS presents MFA/CAPTCHA, run `--headful` and complete it manually once per session if needed.
- Agent is read-only; it does not submit assignments.
- Credentials stay in `.env` and are loaded at runtime via `python-dotenv`/`pydantic`.

## File Map
- `lms_agent/runner.py` — main entrypoint; orchestration and reminder logic.
- `lms_agent/config.py` — env-driven settings.
- `lms_agent/auth.py` — Playwright login/session.
- `lms_agent/fetcher.py` — scraping courses, files, assignments.
- `lms_agent/db.py` — SQLite schema + persistence.
- `lms_agent/notifier.py` — SMTP email sending + dedupe.

## What to tweak for your LMS
- If course cards or assignment listings differ, adjust selectors in `fetcher.py`.
- If the login form uses different field ids/names, update selectors in `auth.py`.
- Tune reminder thresholds in `runner.py` (`THRESHOLDS`).

## Configuration Options
Add these to your `.env` file:
- `CHECK_INTERVAL_MINUTES` — how often to check for updates (default: 60 minutes)
- `HEADLESS=false` — set to `false` to see the browser during login (helpful for debugging)

## Troubleshooting
- If login fails, set `HEADLESS=false` in `.env` and watch the browser; confirm the login form selectors.
- If due dates are not parsed, inspect assignment text and adjust `_extract_due` patterns in `fetcher.py`.
- To reset notifications, remove `lms_agent.db` (you will lose history).
- If the program doesn't detect changes, check that `CHECK_INTERVAL_MINUTES` is set appropriately in `.env`.
=======
