"""MX Player API client and response parsers."""

from __future__ import annotations

import random
import re

import requests

from config import API_BASE, BROWSER_HEADERS, CDN_IMAGE, CDN_VIDEO, DEFAULT_PARAMS, USER_AGENTS


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Parsers (None-safe)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def parse_item(item: dict) -> dict | None:
    """Normalise a raw API item into a flat dict. Returns None for junk."""
    if not isinstance(item, dict):
        return None
    cid = item.get("id", "")
    title = item.get("title", item.get("name", ""))
    if not cid and not title:
        return None

    stream = item.get("stream")
    container = item.get("container") or {}

    return {
        "id": cid,
        "title": title,
        "type": (item.get("type") or "").lower(),
        "description": item.get("description", item.get("synopsis", "")),
        "image": _image_url(item),
        "stream_url": stream_url(stream),
        "stream_options": parse_stream_options(stream),
        "drm": stream.get("drmProtect", False) if isinstance(stream, dict) else False,
        "duration": item.get("duration", 0),
        "sequence": item.get("sequence", ""),
        "year": (item.get("releaseDate") or "")[:4],
        "rating": item.get("rating", ""),
        "languages": item.get("languages") or [],
        "languages_details": _parse_language_details(item),
        "genres": item.get("genres") or [],
        "shareUrl": item.get("shareUrl", ""),
        "firstVideo": item.get("firstVideo"),
        "container": container,
        "publisher": (
            item["publisher"].get("name", "")
            if isinstance(item.get("publisher"), dict)
            else ""
        ),
        "contributors": _contributors(item.get("contributors") or []),
    }


def _image_url(item: dict) -> str:
    for img in item.get("imageInfo") or []:
        if isinstance(img, dict) and img.get("url"):
            u = img["url"]
            return u if u.startswith("http") else f"{CDN_IMAGE}/{u}"
    images = item.get("image") or {}
    if isinstance(images, dict):
        for key in ("16x9", "2x3", "1x1"):
            v = images.get(key)
            if v:
                if v.startswith("http"):
                    return v
                return (
                    f"https://www.mxplayer.in{v}"
                    if v.startswith("/media")
                    else f"{CDN_IMAGE}/{v}"
                )
    return ""


def stream_url(stream) -> str:
    """Extract the best quality stream URL from a stream dict."""
    if not isinstance(stream, dict):
        return ""
    for proto in ("hls", "dash"):
        data = stream.get(proto)
        if isinstance(data, dict):
            for q in ("high", "main", "base"):
                u = data.get(q)
                if u:
                    return u if u.startswith("http") else f"{CDN_VIDEO}/{u}"
    return ""


def parse_stream_options(stream) -> dict:
    """Extract all available stream quality/format URLs.

    Returns: {"hls_high": url, "hls_main": url, "dash_high": url, ...}
    """
    if not isinstance(stream, dict):
        return {}
    options: dict[str, str] = {}
    for proto in ("hls", "dash"):
        data = stream.get(proto)
        if not isinstance(data, dict):
            continue
        for quality in ("high", "main", "base"):
            u = data.get(quality)
            if u:
                options[f"{proto}_{quality}"] = (
                    u if u.startswith("http") else f"{CDN_VIDEO}/{u}"
                )
    return options


def _parse_language_details(item: dict) -> list[dict]:
    """Extract structured language info (id + name) from an item."""
    details = item.get("languagesDetails") or []
    out = []
    for ld in details:
        if isinstance(ld, dict) and ld.get("id"):
            out.append({"id": ld["id"], "name": ld.get("name", ld["id"])})
    if not out:
        for lang in item.get("languages") or []:
            out.append({"id": lang.lower()[:2], "name": lang})
    return out


def _contributors(raw: list) -> list[dict]:
    out = []
    for c in (raw or [])[:8]:
        if isinstance(c, dict) and c.get("name"):
            out.append({"name": c["name"], "role": c.get("type", "")})
    return out


def extract_seasons(detail: dict) -> list[dict]:
    """Pull season info out of a show detail response."""
    seasons = []
    for tab in detail.get("tabs") or []:
        if isinstance(tab, dict) and tab.get("type") == "tvshowepisodes":
            for c in tab.get("containers") or []:
                if isinstance(c, dict) and c.get("id"):
                    seasons.append({
                        "id": c["id"],
                        "title": c.get("title", "Season"),
                        "episodesCount": c.get("episodesCount", 0),
                    })
    return seasons


def show_id_from_episode(ep: dict) -> str:
    """Walk container → container to find the parent tvshow ID."""
    container = ep.get("container") or {}
    show_container = container.get("container") or {}
    return show_container.get("id", "")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API Client
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MXPlayerAPI:
    """Handles all MX Player API interactions."""

    def __init__(self, userid: str):
        self.userid = userid
        self._s = requests.Session()
        self._s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            **BROWSER_HEADERS,
        })

    def _params(self, extra: dict | None = None) -> dict:
        p = {**DEFAULT_PARAMS, "userid": self.userid}
        if extra:
            p.update(extra)
        return p

    # ── Search ─────────────────────────────────────────────

    def search(self, query: str) -> tuple[list[dict], str | None]:
        """Returns (items, error_message)."""
        url = f"{API_BASE}/search/resultv2"
        try:
            r = self._s.post(
                url, params=self._params({"query": query}), json={}, timeout=15
            )
            r.raise_for_status()
            data = r.json()
            items = []
            for section in data.get("sections") or []:
                for item in section.get("items") or []:
                    parsed = parse_item(item)
                    if parsed:
                        items.append(parsed)
            return items, None
        except requests.exceptions.ConnectionError:
            return [], "Network error — could not reach MX Player API."
        except requests.exceptions.Timeout:
            return [], "Request timed out. Please try again."
        except Exception as e:
            return [], f"Search failed: {e}"

    # ── Show / Movie Detail ────────────────────────────────

    def get_collection(self, content_id: str, content_type: str = "tvshow") -> tuple[dict | None, str | None]:
        """Returns (detail_dict, error_message)."""
        url = f"{API_BASE}/detail/collection"
        try:
            r = self._s.get(
                url,
                params=self._params({"type": content_type, "id": content_id}),
                timeout=15,
            )
            if r.status_code == 444:
                return None, None
            r.raise_for_status()
            data = r.json()
            if data.get("id") and data.get("title"):
                return data, None
            return None, None
        except requests.exceptions.ConnectionError:
            return None, "Network error — could not reach MX Player API."
        except Exception as e:
            return None, f"API error: {e}"

    # ── Episodes ───────────────────────────────────────────

    def get_episodes(self, season_id: str) -> tuple[list[dict], str | None]:
        """Returns (episodes, error_message)."""
        url = f"{API_BASE}/detail/tab/tvshowepisodes"
        params = self._params({"type": "season", "id": season_id, "sortOrder": "0"})
        all_episodes: list[dict] = []
        seen_ids: set[str] = set()
        max_pages = 20
        try:
            for _ in range(max_pages):
                r = self._s.get(url, params=params, timeout=15)
                r.raise_for_status()
                data = r.json()
                new_count = 0
                for item in data.get("items") or []:
                    parsed = parse_item(item)
                    if parsed and parsed["id"] not in seen_ids:
                        seen_ids.add(parsed["id"])
                        all_episodes.append(parsed)
                        new_count += 1
                nxt = data.get("next")
                if not nxt or not isinstance(nxt, (int, str)) or new_count == 0:
                    break
                params["next"] = str(nxt)
            return all_episodes, None
        except Exception as e:
            return all_episodes, f"Failed to load episodes: {e}"

    # ── URL Resolution ─────────────────────────────────────

    def resolve_url(self, url: str) -> dict | None:
        """Resolve an MX Player URL to content detail.

        Tries multiple strategies: direct ID lookup, slug-based search.
        Returns dict with keys: type, detail, parsed, seasons, episodes (varies).
        """
        ids = _ids_from_url(url)

        for cid in ids:
            detail, _ = self.get_collection(cid, "tvshow")
            if detail and detail.get("tabs"):
                return {"type": "tvshow", "detail": detail, "parsed": parse_item(detail)}

        for cid in ids:
            detail, _ = self.get_collection(cid, "movie")
            if detail and detail.get("title"):
                return {"type": "movie", "detail": detail, "parsed": parse_item(detail)}

        for cid in ids:
            eps, _ = self.get_episodes(cid)
            if eps:
                sid = show_id_from_episode(eps[0])
                if sid:
                    detail, _ = self.get_collection(sid, "tvshow")
                    if detail:
                        return {"type": "tvshow", "detail": detail, "parsed": parse_item(detail)}
                return {"type": "season", "episodes": eps}

        name = _name_from_url(url)
        if name:
            results, _ = self.search(name)
            if results:
                best = results[0]
                if best["type"] == "tvshow":
                    detail, _ = self.get_collection(best["id"], "tvshow")
                    if detail:
                        return {"type": "tvshow", "detail": detail, "parsed": best}
                return {"type": best["type"], "parsed": best}

        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  URL helpers (used by API client)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _ids_from_url(url: str) -> list[str]:
    return re.findall(r"[a-f0-9]{24,}", url)


def _name_from_url(url: str) -> str:
    """Extract a human-readable name from a MX Player URL slug."""
    for part in url.rstrip("/").split("/"):
        if "watch-" in part:
            clean = re.sub(
                r"-(online|free|full|hd|episodes?|season|all)\b", "", part.replace("watch-", "")
            )
            return clean.replace("-", " ").strip()
    return ""
