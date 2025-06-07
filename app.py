from flask import Flask, request, jsonify, Response
from utils import refresh_cf_cookie
import logging
import asyncio
from threading import Thread
import time
import os
import requests
import subprocess

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

cf_cookie = None  # lazy init


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
        logging.info(f"Proxying path: {endpoint}")
        logging.info(f"Request args: {request.args}")
        logging.info(f"Request headers: {dict(request.headers)}")

        resp = forward_civitai_request(endpoint, request, cf_cookie)

        if resp.status_code == 403:
            app.logger.warning("403! Retrying with fresh cookie...")
            cf_cookie = safe_run_refresh()
            resp = forward_civitai_request(endpoint, request, cf_cookie)

        logging.info(f"Civitai response: {resp.status_code}")
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('Content-Type'))

    except Exception as e:
        logging.error(f"Proxy error: {e}", exc_info=True)
        return jsonify({"error": "Proxy failure", "detail": str(e)}), 500
