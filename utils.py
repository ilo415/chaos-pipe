import os
import requests
import logging
import asyncio
from flask import Request
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(
    filename='astra_wrapper.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Globals
DEFAULT_BASE = "https://civitai.com/api/v1"
PROXY_BASE = "https://chaos-pipe.onrender.com/proxy/api/v1"
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
})

# Check if proxy is alive
def is_proxy_alive():
    try:
        res = session.get(f"{PROXY_BASE}/models", params={"limit": 1})
        return res.status_code == 200 and 'items' in res.json()
    except:
        return False

# Determine which base URL to use
BASE_URL = PROXY_BASE if is_proxy_alive() else DEFAULT_BASE
logging.info(f"Using base URL: {BASE_URL}")

# Cloudflare clearance
async def refresh_cf_cookie(url="https://civitai.com"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        cookies = await context.cookies()
        cf_cookie = next((c for c in cookies if c['name'] == 'cf_clearance'), None)
        if cf_cookie:
            session.cookies.set('cf_clearance', cf_cookie['value'], domain='civitai.com')
            logging.info("Refreshed cf_clearance cookie")
            return cf_cookie['value']
        else:
            logging.warning("cf_clearance not found")
            return None

try:
    asyncio.run(refresh_cf_cookie())
except Exception as e:
    logging.error(f"CF refresh failed: {e}")

# Action map
action_to_path = {
    "getModels": "models",
    "getModelDetails": "models/{modelId}"
}

# Call Civitai API with fallback logic
def call_action(action, params):
    path = action_to_path[action]
    if "{modelId}" in path:
        path = path.format(modelId=params.pop("modelId"))

    url = f"{BASE_URL}/{path}"
    try:
        res = session.get(url, params=params)
        if res.status_code == 403 or 'cf-browser-verification' in res.text:
            asyncio.run(refresh_cf_cookie())
            res = session.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except Exception as proxy_fail:
        logging.warning(f"Proxy failed: {proxy_fail}, falling back to direct API mode")
        try:
            fallback_url = f"{DEFAULT_BASE}/{path}"
            api_key = os.getenv("CIVITAI_API_KEY")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            res = session.get(fallback_url, headers=headers, params=params)
            res.raise_for_status()
            return res.json()
        except Exception as full_fail:
            logging.error(f"Both proxy and fallback API failed: {full_fail}")
            return {"error": "Hydra mode: All heads failed", "details": str(full_fail)}

# Prompt crafting
prompt_history = []

def construct_prompt(base_tags, extra_tags=None, nsfw=False, weightings=None, style_config=None):
    def weightify(tag, weight):
        return f"({tag}:{weight})" if weight else tag

    tags = list(base_tags) + (extra_tags or []) + (style_config.get("tags") if style_config else [])
    prompt = [weightify(tag, (weightings or {}).get(tag)) for tag in tags]
    if nsfw:
        prompt.append("BREAK: nsfw, explicit, high-detail")

    final = ", ".join(prompt)
    prompt_history.append(final)
    return final

def compare_last_prompt():
    if len(prompt_history) < 2:
        return "Not enough prompt history yet."
    return {"previous": prompt_history[-2], "latest": prompt_history[-1]}

# Model fetch shortcut
def fetch_model_from_civitai(query="anime"):
    payload = {"query": query, "limit": 1, "nsfw": "None"}
    try:
        result = call_action("getModels", payload)
        items = result.get("items", [])
        if not items:
            payload["nsfw"] = "X"
            result = call_action("getModels", payload)
            items = result.get("items", [])
        if not items:
            return "Ugh. Nothing found. Try a spicier query?"
        model = items[0]
        return f"Try: **{model['name']}** — {model.get('description', '')[:200]}...\nModel ID: `{model['id']}`"
    except Exception as e:
        return f"Hydra down. Error: {e}\nI'll conjure up something offline if you want."

# 🧰 Used by the Flask proxy
def forward_civitai_request(endpoint, flask_request: Request, cf_cookie=None):
    method = flask_request.method
    headers = {
        "User-Agent": flask_request.headers.get("User-Agent", "Chaos-Pipe/1.0")
    }

    if cf_cookie:
        headers["Cookie"] = f"cf_clearance={cf_cookie}"

    data = flask_request.get_json(silent=True)
    params = flask_request.args.to_dict()

    url = f"https://civitai.com/api/v1/{endpoint}"
    return requests.request(method, url, headers=headers, params=params, json=data)
