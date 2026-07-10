# Instagram Scraper

Paste Instagram links, scrape name / followers / bio + profile photo, let Gemini
add gender and category, and push each result to a webhook — shown as cards in a
simple web app.

## Setup on a new computer

You need **Python 3** installed ([python.org/downloads](https://www.python.org/downloads/)).

### Option A — double-click (macOS)
1. Double-click **`Instagram Scraper.command`** in Finder.
   - First run installs everything automatically.
   - It opens the app in your browser.
2. Edit **`.env`** and paste your Gemini key (see below), then double-click again.

> If macOS blocks it the first time: right-click → **Open** → **Open**.

### Option B — terminal (macOS / Linux)
```bash
./setup.sh      # one-time: creates .venv, installs deps, makes .env
./start.sh      # starts the app and opens the browser
```

## Configuration (`.env`)
`setup.sh` creates `.env` from `.env.example`. Fill in:

```
GEMINI_API_KEY=your-key-here        # free: https://aistudio.google.com/apikey
WEBHOOK_URL=https://.../insta-sheet  # where each profile is POSTed
```

Optional:
```
IG_SESSIONID=...        # force a specific Instagram session cookie
IG_BROWSER=brave        # force which browser to read the cookie from
PORT=5001               # change the local port
```

## Instagram login (automatic)
The app reads your Instagram `sessionid` from whatever browser you're already
logged into (Chrome/Safari/Firefox/Brave/Edge/Chromium/Opera) to avoid rate
limits — **nothing to copy or paste**. Just be logged into instagram.com in a
browser. The header shows `🔓 authenticated` when it found the login.

- **Safari**: give your terminal **Full Disk Access** (System Settings →
  Privacy & Security → Full Disk Access) so it can read Safari's cookies.
- **Chrome/Brave**: approve the one-time keychain prompt.

If no login is found it falls back to anonymous mode (works, but rate-limited).

## Using it
1. Paste up to **10** Instagram links/handles (one per line).
2. Press **Run**. Cards appear one at a time.
3. There's a **15–45s** randomized wait between profiles and a **5-minute**
   cooldown between runs (to stay under Instagram's radar).

## Files
- `app.py` — Flask web server (UI + API)
- `insta.py` — scraping, Gemini, webhook, session cookie logic
- `static/index.html` — the web UI
- `setup.sh` / `start.sh` — install & run
- `Instagram Scraper.command` — double-click launcher (macOS)
