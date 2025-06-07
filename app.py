from flask import Flask, request, jsonify
from utils import refresh_cf_cookie
import logging
import asyncio
from threading import Thread
import time
import os
import requests
import subprocess  # 🔧 for runtime playwright install

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

cf_cookie = None  # lazy init


# 🔁 background cf_cookie auto-refresh with browser install fallback
def periodic_cf_refresh(interval=900):
    global cf_cookie
    while True:
        try:
            app.logger.info("Refreshing cf_cookie in background...")
            cf_cookie = safe_run_refresh()
            app.logger.info("cf_cookie refreshed")
        except Exception as e:
            app.logger.error(f"cf_cookie auto-refresh failed: {e}")
        time.sleep(interval)


def safe_run_refresh():
    try:
        return asyncio.run(refresh_cf_cookie())
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            app.logger.warning("Playwright browser not found, attempting runtime install...")
            subprocess.run(["python", "-m", "playwright", "install", "chromium"], check=True)
            app.logger.info("Playwright browser installed at runtime.")
            return asyncio.run(refresh_cf_cookie())
        else:
            raise


def start_background_tasks():
    t = Thread(target=periodic_cf_refresh, daemon=True)
    t.start()


start_background_tasks()


# 🔐 upgraded proxy logic, now in here
def forward_civitai_request(endpoint, req, cf_cookie):
    headers = dict(req.headers)
    headers["cf_clearance"] = cf_cookie
    headers["User-Agent"] = "ChaosPipe/1.0"

    api_key = req.headers.get("x-api-key") or os.getenv("CIVITAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"https://civitai.com/api/v1/{endpoint}"
    data = req.get_json(silent=True)

    if req.method == "GET":
        return requests.get(url, params=req.args, headers=headers)
    else:
        return requests.post(url, json=data, headers=headers)


@app.route('/')
def index():
    global cf_cookie
    if cf_cookie is None:
        Thread(target=lambda: safe_run_refresh(), daemon=True).start()
        app.logger.info("cf_cookie kickstarted async in index route")
    return "Chaos Pipe proxy is alive."


@app.route('/healthz')
def healthz():
    if cf_cookie:
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "cf_cookie missing"}), 503


@app.route('/proxy/<path:endpoint>', methods=['GET', 'POST'])
def proxy(endpoint):
    global cf_cookie
    try:
        resp = forward_civitai_request(endpoint, request, cf_cookie)
        if resp.status_code == 403:
            app.logger.warning("403! Retrying with fresh cookie...")
            cf_cookie = safe_run_refresh()
            resp = forward_civitai_request(endpoint, request, cf_cookie)
        app.logger.info(f"Proxy response {resp.status_code}: {resp.text[:200]}")
        return (resp.content, resp.status_code, resp.headers.items())
    except Exception as e:
        app.logger.error(f"Proxy error: {e}")
        return jsonify({"error": "Proxy failed", "details": str(e)}), 500
