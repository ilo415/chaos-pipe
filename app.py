# app.py
from flask import Flask, request, jsonify
from utils import refresh_cf_cookie, forward_civitai_request
import logging
import asyncio

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

cf_cookie = None  # lazy init


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
