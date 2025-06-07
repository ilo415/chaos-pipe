from flask import Flask, request, jsonify
from utils import refresh_cf_cookie, forward_civitai_request
import logging
import asyncio
from threading import Thread
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

cf_cookie = None  # lazy init

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
    t = Thread(target=periodic_cf_refresh, daemon=True)
    t.start()

start_background_tasks()

@app.route('/')
def index():
    global cf_cookie
    if cf_cookie is None:
        try:
            cf_cookie = asyncio.run(refresh_cf_cookie())
            app.logger.info("cf_cookie primed at index route")
        except Exception as e:
            app.logger.error(f"Failed to prime cf_cookie: {e}")
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
            cf_cookie = asyncio.run(refresh_cf_cookie())
            resp = forward_civitai_request(endpoint, request, cf_cookie)
        return (resp.content, resp.status_code, resp.headers.items())
    except Exception as e:
        app.logger.error(f"Proxy error: {e}")
        return jsonify({"error": "Proxy failed", "details": str(e)}), 500
