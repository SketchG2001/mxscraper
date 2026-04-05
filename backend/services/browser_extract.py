"""Headless browser extraction of HLS/DASH URLs from an MX Player page."""

from __future__ import annotations

import json
import os
import random
import re
import time

from config import USER_AGENTS
from services.mx_api import MXPlayerAPI, extract_seasons, name_from_url


def extract_and_resolve(url: str, userid: str) -> dict:
    """Load *url* in Chrome, scan performance logs for m3u8/mpd, then resolve.

    Returns a dict suitable for building ``ExtractBrowserResponse``:
    ``type``, ``parsed`` (optional dict), ``detail`` (optional), ``seasons``,
    ``episodes``, ``direct_stream_url``, ``error``.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    for flag in (
        "--headless",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-blink-features=AutomationControlled",
    ):
        opts.add_argument(flag)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    drv_path = os.getenv("CHROMEDRIVER_PATH")
    if not drv_path:
        render = "./chromedriver/chromedriver"
        if os.path.exists(render):
            drv_path = render
    svc = Service(drv_path) if drv_path else Service(ChromeDriverManager().install())

    try:
        driver = webdriver.Chrome(service=svc, options=opts)
    except Exception as exc:
        return {"error": f"Could not start Chrome: {exc}"}

    found_stream: str | None = None
    try:
        driver.get(url)
        time.sleep(random.uniform(4, 7))
        driver.execute_script(f"window.scrollTo(0, {random.randint(100, 300)});")
        time.sleep(random.uniform(1, 2))

        urls: list[str] = []
        for entry in driver.get_log("performance"):
            try:
                msg = json.loads(entry["message"])
                if "Network.responseReceived" in msg["message"]["method"]:
                    rid = msg["message"]["params"]["requestId"]
                    body = driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": rid}
                    ).get("body", "")
                    urls.extend(re.findall(r'https://[^\s\'"]+\.m3u8', body))
                    urls.extend(re.findall(r'https://[^\s\'"]+\.mpd', body))
            except Exception:
                continue

        if urls:
            found_stream = urls[0]
    finally:
        driver.quit()

    if not found_stream:
        return {"error": "Could not find any video stream on this page."}

    api = MXPlayerAPI(userid)
    resolved = api.resolve_url(url)

    if resolved and resolved.get("parsed"):
        out: dict = {
            "type": resolved.get("type", ""),
            "parsed": resolved["parsed"],
            "direct_stream_url": found_stream,
        }
        if resolved["type"] == "tvshow" and resolved.get("detail"):
            out["detail"] = resolved["detail"]
            out["seasons"] = extract_seasons(resolved["detail"])
        if resolved.get("episodes"):
            out["episodes"] = resolved["episodes"]
        return out

    title_guess = name_from_url(url) or "MX Player Video"
    return {
        "type": "video",
        "parsed": {
            "id": "",
            "title": title_guess,
            "type": "video",
            "description": f"Extracted from: {url}",
            "image": "",
            "stream_url": found_stream,
            "drm": False,
            "duration": 0,
            "sequence": "",
            "year": "",
            "rating": "",
            "languages": [],
            "languages_details": [],
            "genres": [],
            "shareUrl": "",
            "publisher": "",
            "contributors": [],
        },
        "direct_stream_url": found_stream,
    }
