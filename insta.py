"""
Instagram -> AI extract -> Webhook
==================================
Reads Instagram handles from `handles.txt` (one per line), fetches each PUBLIC
profile page, and lets Gemini pull out the structured info, then POSTs it to a
webhook as JSON: gender, category, name, handle, followers, bio.

Only public information is used (the same name / followers / bio you'd see in a
browser link preview). Gender is not published by Instagram, so Gemini makes a
best-guess from the name/bio (or returns "" if unsure).

============================ ONE-TIME SETUP ============================
     pip install requests

  Get a free Gemini API key: https://aistudio.google.com/apikey
  Then either set it as an env var (recommended):
        export GEMINI_API_KEY="your-key-here"
  ...or paste it into GEMINI_API_KEY below.

============================ RUN ============================
     - Paste handles into handles.txt (one per line, @ optional)
     - python insta.py
"""

import os
import re
import html
import json
import time
import base64
import random
import unicodedata
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass  # dotenv is optional; env vars still work without it

# ----------------------------- SETTINGS --------------------------------------

INPUT_FILE = "handles.txt"

WEBHOOK_URL = os.environ.get(
    "WEBHOOK_URL", "https://w7pl1yv5.rpcl.dev/webhook-test/insta-sheet"
)

USE_GEMINI = True                                    # set True once the Gemini key works
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")   # loaded from .env
GEMINI_MODEL = "gemini-3.1-flash-lite"                  # free-tier friendly

# Politeness delay between profiles (seconds). Bigger = slower but safer.
MIN_DELAY = 10
MAX_DELAY = 20

HEADERS = ["gender", "category", "name", "handle", "followers", "bio"]

BASE_DIR = Path(__file__).resolve().parent

BROWSER_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 12_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
)
# App id required by Instagram's public web_profile_info endpoint.
IG_APP_ID = "936619743392459"

# Use a logged-in Instagram session (from your browser) to lift rate limits.
USE_SESSION_COOKIE = True
# Optional manual override: paste a sessionid here or in .env as IG_SESSIONID.
IG_SESSIONID = os.environ.get("IG_SESSIONID", "")
# Restrict which browser to read (e.g. "brave", "chrome", "safari"). "" = try all.
IG_BROWSER = os.environ.get("IG_BROWSER", "")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# The ONLY categories allowed. Gemini may pick one or more of these (or none).
ALLOWED_CATEGORIES = {"Celebrity", "Lifestyle", "Creative", "Model", "Fitness"}
CATEGORY_DEFINITIONS = """- Celebrity: anyone with a TV show or movie, an actor, or a singer
- Lifestyle: anyone with mixed beauty, fashion, and/or food content
- Creative: any photographer, videographer, painter, etc.
- Model: someone who works as a model
- Fitness: anyone with exercise or healthy-living content"""

EXTRACT_PROMPT = """You are cleaning up scraped public data about an Instagram profile.

Handle: @{handle}

Scraped profile data (JSON):
{meta}

A profile picture may be attached. When the bio is empty or unhelpful, use the
image as an additional signal for both gender and category (e.g. gym/workout
shots -> FITNESS, a modelling headshot -> MODEL, camera/artwork -> CREATIVE).

Return ONLY a JSON object with these exact keys:
- "name": the person's real name in plain Latin letters. Convert stylized or
  decorative fonts (e.g. 𝕡𝕒𝕦𝕝𝕒, ＡＮＤＲＡ) to normal text and remove emojis. If the
  value is not an actual person's name (a description, tagline, slogan, or a
  single stray letter), return "".
- "gender": best guess "MALE", "FEMALE", or "Not Specified" if unclear (from name/bio/photo)
- "followers": follower count as an integer (0 if unknown)
- "bio": the profile bio text, cleaned to a single line (string, "" if unknown)
- "category": an array of EVERY label below that applies (a profile can match
  several). Return [] if none clearly fit. Use the label text exactly as written
  below, nothing else:
{categories}

Use the scraped data as the source of truth. Do not invent numbers.
Never output a category outside the list above."""

# -----------------------------------------------------------------------------


def load_handles(path: str):
    handles = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            h = line.strip().lstrip("@")
            if h:
                handles.append(h)
    return handles


def clean_name(name: str) -> str:
    """De-stylize a display name into plain text.

    Handles fancy Unicode fonts (𝕡𝕒𝕦𝕝𝕒 -> paula), fullwidth text (ＡＮＤＲＡ ->
    ANDRA) and strips emoji / decorative symbols. Real-name-vs-tagline judgement
    is left to Gemini; this is just the character-level cleanup.
    """
    if not name:
        return ""
    # NFKC folds decorative/fullwidth code points back to plain Latin.
    n = unicodedata.normalize("NFKC", name)
    kept = []
    for ch in n:
        # Drop zero-width joiners and variation selectors (invisible emoji glue).
        if ch in "‍︎️" or 0xFE00 <= ord(ch) <= 0xFE0F:
            continue
        cat = unicodedata.category(ch)
        # Keep letters, marks (accents), numbers, spaces and basic name punctuation.
        if cat[0] in ("L", "M", "N") or cat == "Zs" or ch in " '.-&":
            kept.append(ch)
        # Everything else (emoji, symbols, flags, arrows) is dropped.
    cleaned = re.sub(r"\s+", " ", "".join(kept)).strip(" .,-&")
    return cleaned


def _parse_count(text: str) -> int:
    """Turn '382K' / '1.2M' / '2,357' into an int."""
    t = text.strip().replace(",", "").upper()
    mult = 1
    if t.endswith("K"):
        mult, t = 1_000, t[:-1]
    elif t.endswith("M"):
        mult, t = 1_000_000, t[:-1]
    elif t.endswith("B"):
        mult, t = 1_000_000_000, t[:-1]
    try:
        return int(float(t) * mult)
    except ValueError:
        return 0


_ig_session = None
_ig_auth_note = "not initialized"
_ig_browser_used = ""
_ig_diag = []  # human-readable notes from the last login-detection attempt
_ig_last_diag_printed = ""  # to avoid re-printing the same diagnostics


def _firefox_profile_dirs():
    """Every Firefox profile directory on this machine, across OSes.

    Covers a normal Firefox install and the Microsoft Store version, which
    sandboxes its profile under %LOCALAPPDATA%\\Packages\\Mozilla.Firefox_*.
    """
    roots = []
    home = Path.home()
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if appdata:                                        # Windows, normal install
        roots.append(Path(appdata) / "Mozilla" / "Firefox" / "Profiles")
    if localappdata:                                   # Windows, Microsoft Store
        store = Path(localappdata) / "Packages"
        try:
            for pkg in store.glob("Mozilla.Firefox_*"):
                roots.append(pkg / "LocalCache" / "Roaming" / "Mozilla" / "Firefox" / "Profiles")
        except Exception:
            pass
    roots += [
        home / "Library" / "Application Support" / "Firefox" / "Profiles",  # macOS
        home / ".mozilla" / "firefox",                                      # Linux
        home / "snap" / "firefox" / "common" / ".mozilla" / "firefox",      # Linux snap
        home / ".var" / "app" / "org.mozilla.firefox" / ".mozilla" / "firefox",  # Flatpak
    ]
    dirs = []
    for root in roots:
        try:
            if root.is_dir():
                dirs += [p for p in root.iterdir() if p.is_dir()]
        except Exception:
            continue
    return dirs


def _sessionid_from_firefox(bc):
    """Try every Firefox profile's cookie DB for an Instagram sessionid.

    browser_cookie3 only reads the single 'default' profile, so a login saved
    in any other profile is invisible to it. We enumerate them all instead.
    Returns (sessionid, note) — note describes what was found for logging.
    """
    profiles = _firefox_profile_dirs()
    if not profiles:
        return "", "no Firefox profile folder found"

    checked = 0
    for prof in profiles:
        cookie_db = prof / "cookies.sqlite"
        if not cookie_db.exists():
            continue
        checked += 1
        try:
            for c in bc.firefox(cookie_file=str(cookie_db), domain_name="instagram.com"):
                if c.name == "sessionid" and c.value:
                    return c.value, f"found in Firefox profile '{prof.name}'"
        except Exception as e:
            _ig_diag.append(f"firefox profile '{prof.name}': {type(e).__name__}: {e}")
            continue
    if checked == 0:
        return "", "Firefox profiles exist but none have a cookies.sqlite yet"
    return "", f"checked {checked} Firefox profile(s) — no Instagram sessionid found"


def _load_sessionid() -> str:
    """Find an Instagram sessionid automatically.

    Order: explicit IG_SESSIONID -> every Firefox profile -> other browsers
    (via browser_cookie3). Returns "" if none found. Diagnostics for each step
    are appended to _ig_diag and printed to the server console.

    Note on Windows: Chrome and Edge (v127+, mid-2024 onward) encrypt cookies
    with "app-bound encryption", which only the browser itself can decrypt, so
    no outside tool can read them. Firefox does NOT do this, so it's tried first
    and is the reliable choice for automatic login on Windows.
    """
    global _ig_browser_used
    _ig_diag.clear()

    if IG_SESSIONID:
        _ig_browser_used = "manual override (IG_SESSIONID)"
        return IG_SESSIONID
    try:
        import browser_cookie3 as bc
    except ImportError:
        _ig_diag.append("browser_cookie3 is not installed")
        return ""

    # Firefox first (readable on Windows, unlike Chrome/Edge), checking every profile.
    if not IG_BROWSER or IG_BROWSER == "firefox":
        sid, note = _sessionid_from_firefox(bc)
        _ig_diag.append(note)
        if sid:
            _ig_browser_used = "firefox"
            return sid

    # Then the rest, via browser_cookie3's default single-profile lookup.
    other = {
        "chrome": bc.chrome, "edge": bc.edge, "brave": bc.brave,
        "chromium": bc.chromium, "opera": bc.opera, "safari": bc.safari,
    }
    if IG_BROWSER:
        other = {IG_BROWSER: other[IG_BROWSER]} if IG_BROWSER in other else {}

    for name, fn in other.items():
        try:
            for c in fn(domain_name="instagram.com"):
                if c.name == "sessionid" and c.value:
                    _ig_browser_used = name
                    return c.value
        except Exception as e:
            # Not installed, locked, or (Chrome/Edge on Windows) encrypted.
            _ig_diag.append(f"{name}: {type(e).__name__}: {e}")
            continue
    return ""


def get_session() -> requests.Session:
    """A shared requests session, logged in via a browser cookie if available.

    Once a login is found the session is cached. While still anonymous we retry
    detection on every call, so logging into Firefox and reloading the page
    picks up the new login without having to restart the app.
    """
    global _ig_session, _ig_auth_note
    if _ig_session is not None and "authenticated" in _ig_auth_note:
        return _ig_session

    s = requests.Session()
    s.headers.update({"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"})
    if USE_SESSION_COOKIE:
        sid = _load_sessionid()
        if sid:
            s.cookies.set("sessionid", sid, domain=".instagram.com")
            where = f" from {_ig_browser_used}" if _ig_browser_used else ""
            _ig_auth_note = f"authenticated (using logged-in session{where})"
        else:
            _ig_auth_note = (
                "anonymous — no Instagram login found. Log in to Instagram in "
                "Firefox (a normal window, not Private Browsing), then reload "
                "this page. (Windows blocks reading the login from Chrome/Edge, "
                "so Firefox is needed.)"
            )
            # Print what we found so the terminal shows why detection failed,
            # but only when it changes - status is polled often and we don't
            # want to spam the console every second.
            global _ig_last_diag_printed
            snapshot = "\n".join(_ig_diag)
            if snapshot != _ig_last_diag_printed:
                _ig_last_diag_printed = snapshot
                print("==> Instagram login detection:")
                for line in _ig_diag or ["(no diagnostics captured)"]:
                    print(f"    - {line}")
    else:
        _ig_auth_note = "anonymous (session cookie disabled)"
    _ig_session = s
    return s


def fetch_profile(handle: str) -> dict:
    """Scrape the public profile page (https://www.instagram.com/<handle>/).

    Reads the profile info from the page's Open Graph meta tags.
    Raises if the page can't be loaded.
    """
    url = f"https://www.instagram.com/{handle}/"
    resp = get_session().get(url, timeout=30)
    resp.raise_for_status()
    html_text = resp.text

    def meta(pattern):
        m = re.search(pattern, html_text, re.I | re.S)
        return html.unescape(m.group(1)) if m else ""

    pic = meta(r'<meta property="og:image" content="(.*?)"\s*/?>')
    # The name="description" tag carries it all:
    #   "382K Followers, 2,357 Following, 214 Posts - NAME (@handle) on Instagram: \"BIO\""
    desc = meta(r'<meta content="(.*?)" name="description"\s*/?>') \
        or meta(r'<meta name="description" content="(.*?)"\s*/?>')

    # Followers count (rounded, e.g. "382K").
    followers = 0
    fm = re.search(r"([\d.,]+[KMB]?)\s+Followers", desc, re.I)
    if fm:
        followers = _parse_count(fm.group(1))

    # Display name: 'Posts - NAME (@handle)'. Absent when there's no display name.
    name = ""
    nm = re.search(r"Posts\s*-\s*(.*?)\s*\(@", desc)
    if nm:
        name = nm.group(1).strip()

    # Bio: everything inside the quotes after 'on Instagram:'.
    bio = ""
    bm = re.search(r'on Instagram:\s*"(.*)"\s*$', desc, re.S)
    if bm:
        bio = bm.group(1).strip()

    return {
        "full_name": name,
        "username": handle,
        "biography": bio,
        "followers": followers,
        "category_name": "",      # not exposed on the public page HTML
        "is_business": None,
        "external_url": "",
        "profile_pic_url": pic,
        "is_verified": False,
    }


def _fetch_image_part(url: str):
    """Download the profile picture and return it as a Gemini inline_data part."""
    if not url:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=20)
        r.raise_for_status()
        mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
        if not mime.startswith("image/"):
            mime = "image/jpeg"
        data = base64.b64encode(r.content).decode("ascii")
        return {"inline_data": {"mime_type": mime, "data": data}}
    except requests.RequestException:
        return None


def ai_extract(handle: str, profile: dict) -> dict:
    """Ask Gemini to turn the scraped profile into cleaned structured fields.

    Attaches the profile picture so Gemini can infer category/gender when the
    bio is empty or unhelpful.
    """
    meta = json.dumps(profile, ensure_ascii=False, indent=2)
    prompt = EXTRACT_PROMPT.format(
        handle=handle, meta=meta, categories=CATEGORY_DEFINITIONS
    )
    parts = [{"text": prompt}]
    img_part = _fetch_image_part(profile.get("profile_pic_url", ""))
    if img_part:
        parts.append(img_part)
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    resp = requests.post(
        GEMINI_ENDPOINT,
        params={"key": GEMINI_API_KEY},
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def normalize_handle(text: str) -> str:
    """Turn a pasted @handle or instagram.com URL into a bare username."""
    t = text.strip()
    if not t:
        return ""
    if "instagram.com" in t:
        # https://www.instagram.com/<handle>/... -> <handle>
        after = t.split("instagram.com/", 1)[1]
        t = after.split("/", 1)[0].split("?", 1)[0]
    return t.lstrip("@").strip()


def clean_categories(raw_cats) -> list:
    """Normalize Gemini's category output to the allowed uppercase labels."""
    if isinstance(raw_cats, str):
        raw_cats = [raw_cats]
    canonical = {c.upper(): c for c in ALLOWED_CATEGORIES}
    cats = [canonical.get(c.strip().upper()) for c in (raw_cats or [])]
    cats = [c for c in cats if c]
    return list(dict.fromkeys(cats))  # dedupe, keep order


def process_handle(handle: str) -> dict:
    """Scrape one profile (+ optional Gemini) into a normalized result dict."""
    profile = fetch_profile(handle)
    link = f"https://www.instagram.com/{handle}/"

    if USE_GEMINI:
        data = ai_extract(handle, profile)
        gender = data.get("gender", "") or ""
        categories = clean_categories(data.get("category", []))
        name = data.get("name", "") or profile["full_name"]
        followers = data.get("followers", "") or profile["followers"]
        bio = data.get("bio", "") or profile["biography"]
    else:
        gender = ""
        categories = clean_categories(profile["category_name"])
        name = profile["full_name"]
        followers = profile["followers"]
        bio = profile["biography"]

    name = clean_name(name)  # de-stylize fonts / strip emoji as a final safety net

    return {
        "gender": gender,
        "categories": categories,
        "category": ", ".join(categories),
        "name": name,
        "handle": handle,
        "link": link,
        "followers": followers,
        "bio": bio,
        "profile_pic_url": profile.get("profile_pic_url", ""),
        "is_verified": profile.get("is_verified", False),
    }


def send_row(row) -> bool:
    """POST one row to the webhook as JSON keyed by column name. Returns success."""
    payload = dict(zip(HEADERS, row))
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"        ! webhook POST failed: {e}")
        return False


def main():
    if USE_GEMINI and not GEMINI_API_KEY:
        print("No Gemini API key. Set GEMINI_API_KEY env var or paste it into the script.")
        print("Get a free key at: https://aistudio.google.com/apikey")
        return
    if not WEBHOOK_URL:
        print("Please paste your webhook URL into WEBHOOK_URL at the top of the script.")
        return

    get_session()  # initialize + detect login
    print(f"Instagram: {_ig_auth_note}")

    handles = load_handles(str(BASE_DIR / INPUT_FILE))
    print(f"Found {len(handles)} handles to process.\n")

    for i, handle in enumerate(handles, 1):
        try:
            r = process_handle(handle)
            print(f"[{i}/{len(handles)}] OK   @{handle} — {r['name']} — {r['followers']:,} followers — {r['category']}")
            row = [r["gender"], r["category"], r["name"], r["link"], r["followers"], r["bio"]]
        except Exception as e:
            row = ["", "", f"ERROR: {type(e).__name__}", handle, "", ""]
            print(f"[{i}/{len(handles)}] ERR  @{handle} — {e}")

        send_row(row)

        if i < len(handles):
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    print("\nDone — all rows posted to your webhook.")


if __name__ == "__main__":
    main()
