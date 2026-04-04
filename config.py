"""Shared constants and configuration for the MX Player scraper."""

API_BASE = "https://api.mxplayer.in/v1/web"
CDN_IMAGE = "https://qqcdnpictest.mxplay.com"
CDN_VIDEO = "https://llvod.mxplay.com"

DEFAULT_PARAMS = {
    "device-density": "3",
    "platform": "com.mxplay.desktop",
    "content-languages": "hi,en",
    "kids-mode-enabled": "false",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]

BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Origin": "https://www.mxplayer.in",
    "Referer": "https://www.mxplayer.in/",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}

SESSION_DEFAULTS = {
    "userid": None,
    "page": "home",
    "search_results": [],
    "selected_content": None,
    "show_detail": None,
    "seasons": [],
    "sel_season_idx": 0,
    "episodes": [],
    "episodes_season_id": None,
    "playing_episode_id": None,
    # download state
    "dl_status": "idle",       # idle | downloading | paused | completed | error
    "dl_progress": 0.0,        # 0-100
    "dl_file": None,
    "dl_title": "",
    "dl_error": None,
    "dl_pid": None,
    "dl_proc": None,
    "dl_log": None,
}
