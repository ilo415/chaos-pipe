import requests
from flask import Request

# Grab Cloudflare cookie
def get_cf_cookie():
    url = "https://civitai.com/api/v1/models?limit=1"
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Referer": "https://civitai.com/",
        "Origin": "https://civitai.com",
    }
    session.get(url, headers=headers)
    return session.cookies.get_dict().get("cf_clearance")


# Forward a request to Civitai using the captured cookie
def forward_civitai_request(endpoint: str, req: Request, cf_cookie: str):
    url = f"https://civitai.com/api/v1/{endpoint}"
    headers = {
        "User-Agent": req.headers.get("User-Agent", "Mozilla/5.0"),
        "Content-Type": req.headers.get("Content-Type", "application/json"),
        "Referer": "https://civitai.com/",
        "Origin": "https://civitai.com",
        "Cookie": f"cf_clearance={cf_cookie}"
    }

    try:
        if req.method == "GET":
            resp = requests.get(url, headers=headers, params=req.args)
        else:
            data = req.get_json(silent=True) or req.form or None
            resp = requests.post(url, headers=headers, json=data)

        # Debug log
        print(f"[PROXY DEBUG] {url} → {resp.status_code}")
        print(f"[PROXY DEBUG] Response text (truncated): {resp.text[:300]}")
        return resp
    except Exception as e:
        print(f"[PROXY ERROR] {e}")
        raise
