import requests
from flask import Request

def get_cf_cookie():
    url = "https://civitai.com/api/v1/models?limit=1"
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
    }
    session.get(url, headers=headers)
    return session.cookies.get_dict().get("cf_clearance")

def forward_civitai_request(endpoint: str, req: Request, cf_cookie: str):
    url = f"https://civitai.com/api/v1/{endpoint}"
    headers = {
        "User-Agent": req.headers.get("User-Agent", "Mozilla/5.0"),
        "Content-Type": req.headers.get("Content-Type", "application/json"),
        "Cookie": f"cf_clearance={cf_cookie}"
    }
    if req.method == "GET":
        return requests.get(url, headers=headers, params=req.args)
    else:
        return requests.post(url, headers=headers, json=req.json)
