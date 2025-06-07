from flask import Flask, request, jsonify
from utils import refresh_cf_cookie
import logging
import asyncio
from threading import Thread
import time
import os
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

cf_cookie = None  # lazy init

# 🔁 background cf_cookie auto-refresh
def periodic_cf_refresh(interval=900):
    global cf_cookie
    while True:
        try:
            app.logger.info("Refreshing cf_cookie in background...")
            cf_cookie = asyncio.run(refresh_cf_cookie())
            app.logger.info("cf_cookie refreshed")
        except Exception as e:
            app.logger.error(f"cf_cookie auto-refresh failed: {e}")
        time.sleep(interval)

def start_background_tasks():
    # ⏩ Don't block startup — just kick off auto-refresh
    t = Thread(target=periodic_cf_refresh, daemon=True)
    t.start()

start_background_tasks()

# 🔐 upgraded proxy logic, now in here
def forward_civitai_request(endpoint, req, cf_cookie):
    headers = dict(req.headers)
    headers["cf_clearance"] = cf_cookie
    headers["User-Agent"] = "ChaosPipe/1.0"

    # 🧠 override with x-api-key if present
    api_key = req.headers.get("x-api-key") or os.getenv("CIVITAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"https://civitai.com/api/v1/{endpoint}"
    data = req.get_json(silent=True)

    if req.method == "GET":
        return requests.get(url, params=req.args, headers=headers)
    else:
        return requests.post(url, json=data, headers=headers)

# ✅ sanity check route
@app.route('/')
def index():
    global cf_cookie
    if cf_cookie is None:
        Thread(target=lambda: asyncio.run(refresh_cf_cookie()), daemon=True).start()
        app.logger.info("cf_cookie kickstarted async in index route")
    return "Chaos Pipe proxy is alive."

# 💓 health ping
@app.route('/healthz')
def healthz():
    if cf_cookie:
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "cf_cookie missing"}), 503

# 🚪 smart proxy with x-api-key override
@app.route('/proxy/<path:endpoint>', methods=['GET', 'POST'])
def proxy(endpoint):
    global cf_cookie
    try:
        resp = forward_civitai_request(endpoint, request, cf_cookie)
        if resp.status_code == 403:
            app.logger.warning("403! Retrying with fresh cookie...")
            cf_cookie = asyncio.run(refresh_cf_cookie())
            resp = forward_civitai_request(endpoint, request, cf_cookie)
        app.logger.info(f"Proxy response {resp.status_code}: {resp.text[:200]}")
        return (resp.content, resp.status_code, resp.headers.items())
    except Exception as e:
        app.logger.error(f"Proxy error: {e}")
        return jsonify({"error": "Proxy failed", "details": str(e)}), 500
