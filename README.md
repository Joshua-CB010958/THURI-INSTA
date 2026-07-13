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

### Option C — Windows
`setup.sh` / `start.sh` are bash scripts and won't run in cmd or PowerShell — use
the `.ps1` versions. **Python is not required up front**: `setup.ps1` installs it
for you (via `winget`, falling back to the official installer) if it isn't there.

> **Double-click the `.bat` files, never the `.ps1` files.** Windows opens a
> double-clicked `.ps1` in Notepad instead of running it — that's a deliberate
> security default, not something being broken. The `.bat` files are wrappers
> that run the `.ps1` properly. (Right-click → **Run with PowerShell** also
> works.)

**If you already have the project folder** — double-click
**`Instagram Scraper.bat`**. That's it: it installs Python if needed, installs
the dependencies and opens the app. It downloads no project files.

**From a bare machine, with no copy of the project.** Open **PowerShell**
(Start → type "PowerShell" → Enter) and paste:

```powershell
iwr -useb https://raw.githubusercontent.com/Joshua-CB010958/THURI-INSTA/main/bootstrap.ps1 | iex
```

That fetches the project into `%USERPROFILE%\THURI-INSTA`, installs Python if
missing, installs the dependencies, and starts the app in your browser.

**Step by step, if you'd rather see what's happening.** From inside the folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1   # one-time
powershell -ExecutionPolicy Bypass -File .\start.ps1   # starts the app
```

Downloading `setup.sh` (or `setup.ps1`) on its own does nothing — it needs
`app.py`, `insta.py`, `requirements.txt` and `static/` sitting next to it.

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

- **Safari** (macOS): give your terminal **Full Disk Access** (System Settings →
  Privacy & Security → Full Disk Access) so it can read Safari's cookies.
- **Chrome/Brave** (macOS): approve the one-time keychain prompt.
- **Windows**: nothing to approve — Chrome/Edge/Firefox/Brave cookies are read
  directly. (Safari doesn't exist there, so ignore the Safari note.)

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
- `setup.sh` / `start.sh` — install & run (macOS / Linux)
- `setup.ps1` / `start.ps1` — install & run (Windows)
- `Instagram Scraper.command` — double-click launcher (macOS)
- `Instagram Scraper.bat` — double-click launcher (Windows)
- `bootstrap.ps1` / `bootstrap.bat` — download-and-run, for a machine with nothing installed
