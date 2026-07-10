#!/usr/bin/env bash
# One-time setup: creates a virtualenv, installs dependencies, and prepares .env.
# Safe to re-run.
set -e
cd "$(dirname "$0")"

echo "==> Instagram Scraper setup"

# 1. Find Python 3.
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "!! Python 3 is not installed. Install it from https://www.python.org/downloads/ and re-run."
  exit 1
fi
echo "==> Using $($PY --version)"

# 2. Create the virtualenv if missing.
if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment (.venv)"
  $PY -m venv .venv
fi

# 3. Install dependencies.
echo "==> Installing dependencies"
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

# 4. Create .env from the template if it doesn't exist yet.
if [ ! -f ".env" ]; then
  echo "==> Creating .env from template"
  cp .env.example .env
  echo "   -> Edit .env and add your GEMINI_API_KEY (https://aistudio.google.com/apikey)"
fi

echo ""
echo "==> Setup complete."
echo "    1. Put your Gemini key in .env (GEMINI_API_KEY=...)"
echo "    2. Log into Instagram in your browser (Chrome/Safari/Brave/etc.)"
echo "    3. Start the app:   ./start.sh"
