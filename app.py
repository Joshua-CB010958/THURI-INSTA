"""
Instagram scraper web app
=========================
Paste one or many Instagram links/handles, press Run, and see result cards.

Run:
    .venv/bin/pip install flask
    .venv/bin/python app.py
    open http://127.0.0.1:5000
"""

from flask import Flask, request, jsonify, send_from_directory, Response

import requests

import insta

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def status():
    insta.get_session()  # ensure session/auth detection has run
    authed = "authenticated" in insta._ig_auth_note
    return jsonify({"authed": authed, "note": insta._ig_auth_note})


@app.route("/api/scrape", methods=["POST"])
def scrape():
    """Scrape a single handle and return its normalized result dict."""
    data = request.get_json(silent=True) or {}
    handle = insta.normalize_handle(data.get("handle", ""))
    if not handle:
        return jsonify({"ok": False, "error": "empty handle"}), 400
    try:
        result = insta.process_handle(handle)
        # Push the Gemini output to the webhook (gender, category, name, link, followers, bio).
        row = [
            result["gender"], result["category"], result["name"],
            result["link"], result["followers"], result["bio"],
        ]
        sent = insta.send_row(row)
        result["sent_to_webhook"] = sent
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "handle": handle, "error": f"{type(e).__name__}: {e}"}), 200


@app.route("/api/img")
def img_proxy():
    """Proxy an Instagram CDN image so it isn't blocked by hotlink protection."""
    url = request.args.get("url", "")
    if "cdninstagram" not in url and "fbcdn" not in url:
        return "", 400
    try:
        r = requests.get(url, headers={"User-Agent": insta.BROWSER_UA}, timeout=20)
        return Response(r.content, content_type=r.headers.get("Content-Type", "image/jpeg"))
    except requests.RequestException:
        return "", 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
