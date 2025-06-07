import requests
from flask import Request

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

def forward_civitai_request(endpoint: str, req: Request, cf_cookie: str):
    url = f"https://civitai.com/{endpoint}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Referer": "https://civitai.com/",
        "Origin": "https://civitai.com",
        "Accept": "application/json",
        "Cookie": f"cf_clearance={cf_cookie}"
    }

    params = req.args
    data = req.get_json(silent=True) or req.form or None

    return requests.request(req.method, url, headers=headers, params=params, json=data)
