#!/usr/bin/env bash
# Starts the Instagram Scraper web app and opens it in your browser.
set -e
cd "$(dirname "$0")"

# Run setup automatically if the venv isn't there yet.
if [ ! -d ".venv" ]; then
  echo "==> First run — setting up..."
  ./setup.sh
fi

PORT="${PORT:-5001}"
URL="http://127.0.0.1:${PORT}"

# Open the browser shortly after the server starts.
# Open in Firefox so the app and the Instagram login live in the same browser
# (the login is read from Firefox). Fall back to the default browser if Firefox
# isn't installed.
( sleep 2
  if command -v open >/dev/null 2>&1; then                       # macOS
    open -a "Firefox" "$URL" 2>/dev/null || open "$URL"
  elif command -v firefox >/dev/null 2>&1; then                  # Linux
    firefox "$URL" >/dev/null 2>&1 &
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL"
  fi
) &

echo "==> Starting Instagram Scraper at $URL  (press Ctrl+C to stop)"
PORT="$PORT" ./.venv/bin/python app.py
