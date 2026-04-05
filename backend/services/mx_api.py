"""MX Player API client and response parsers."""

from __future__ import annotations

import random
import re
import urllib.parse

import requests

from config import (
    BROWSER_HEADERS,
    DEFAULT_PARAMS,
    USER_AGENTS,
    settings,
)

API_BASE = settings.api_base
CDN_IMAGE = settings.cdn_image
CDN_VIDEO = settings.cdn_video


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


def hero_banner_url(detail: dict) -> str:
    """Desktop carousel hero from MX ``titleContentImageInfo`` (mxplayer.in home pattern)."""
    for img in detail.get("titleContentImageInfo") or []:
        if not isinstance(img, dict):
            continue
        if img.get("type") != "banner_and_static_bg_desktop":
            continue
        u = (img.get("url") or "").strip()
        if not u:
            continue
        return u if u.startswith("http") else f"{CDN_IMAGE}/{u}"
    return ""


def _root_collection_type(content_type: str) -> str | None:
    """``/detail/collection/root`` works for tvshow + episode on MX; movies use posters only."""
    x = (content_type or "tvshow").lower()
    if x == "episode":
        return "episode"
    if x in ("movie", "video", "music_video", "shortvideos", "trailer", "clip"):
        return None
    return "tvshow"


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
    """Extract a stream URL for playback (main before high for browser/proxy reliability)."""
    if not isinstance(stream, dict):
        return ""
    for proto in ("hls", "dash"):
        data = stream.get(proto)
        if isinstance(data, dict):
            for q in ("main", "high", "base"):
                u = data.get(q)
                if u:
                    return u if u.startswith("http") else f"{CDN_VIDEO}/{u}"
    return ""


def prefer_main_if_default_is_high(url: str, options: dict) -> str:
    """Episodes often default to ``hls_high``; main tends to work more reliably via proxy."""
    if not isinstance(options, dict):
        return (url or "").strip()

    def abs_video(x: str) -> str:
        s = (x or "").strip()
        if not s:
            return ""
        return s if s.startswith("http") else f"{CDN_VIDEO}/{s}"

    u_abs = abs_video(url)
    high_abs = abs_video(options.get("hls_high") or "")
    main_abs = abs_video(options.get("hls_main") or "")
    if high_abs and main_abs and u_abs == high_abs:
        return main_abs
    return (url or "").strip()


def parse_stream_options(stream) -> dict:
    """Extract all available stream quality/format URLs."""
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
    """Walk container -> container to find the parent tvshow ID."""
    container = ep.get("container") or {}
    show_container = container.get("container") or {}
    return show_container.get("id", "")


def format_duration(seconds) -> str:
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return ""
    if s <= 0:
        return ""
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m" if h else f"{m}m"


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

    # Homepage rails: search for candidates, then enrich via the same
    # ``GET /detail/collection/root`` endpoint the mxplayer.in carousel uses
    # (``type=tvshow|episode`` + ``id`` → ``containerItem`` + hero banner assets).
    _BANNER_SEARCH_QUERIES: tuple[str, ...] = (
        "popular web series",
        "hindi movies",
        "mx originals",
        "latest shows",
        "bollywood movies",
    )

    def get_collection_root(
        self, content_type: str, content_id: str
    ) -> tuple[dict | None, str | None]:
        """MX web carousel/detail root — returns ``containerItem`` or None."""
        url = f"{API_BASE}/detail/collection/root"
        try:
            r = self._s.get(
                url,
                params=self._params({
                    "type": (content_type or "tvshow").lower(),
                    "id": content_id,
                }),
                timeout=15,
            )
            if r.status_code == 444:
                return None, None
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict) or data.get("message") != "ok":
                return None, None
            ci = data.get("containerItem")
            if isinstance(ci, dict) and ci.get("id"):
                return ci, None
            return None, None
        except requests.exceptions.ConnectionError:
            return None, "Network error — could not reach MX Player API."
        except Exception as e:
            return None, f"API error: {e}"

    def fetch_home_banners(self, limit: int = 12) -> tuple[list[dict], str | None]:
        """Banner rows: search candidates + ``/detail/collection/root`` hero when supported."""
        cap = max(4, min(int(limit), 24))
        candidates: list[dict] = []
        seen: set[str] = set()
        last_err: str | None = None

        for query in self._BANNER_SEARCH_QUERIES:
            items, err = self.search(query)
            if err:
                last_err = err
            for it in items:
                cid = it.get("id")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                candidates.append(it)
                if len(candidates) >= cap * 3:
                    break
            if len(candidates) >= cap * 3:
                break

        banners: list[dict] = []
        for it in candidates:
            if len(banners) >= cap:
                break
            rt = _root_collection_type(it.get("type") or "tvshow")
            ci: dict | None = None
            if rt:
                ci, _ = self.get_collection_root(rt, it["id"])
            merged = dict(it)
            if ci:
                p2 = parse_item(ci)
                if p2:
                    merged = {**it, **p2}
            hero = hero_banner_url(ci) if ci else ""
            img = (merged.get("image") or "").strip()
            backdrop = hero or img
            if not backdrop:
                continue
            if not img:
                img = backdrop
            desc = (merged.get("description") or "").strip()
            genres: list[str] = []
            langs: list[str] = []
            if ci:
                g = ci.get("genres") or []
                if isinstance(g, list):
                    genres = [str(x) for x in g[:8] if x]
                lg = ci.get("languages") or []
                if isinstance(lg, list):
                    langs = [str(x) for x in lg[:6] if x]
            rt_str = (merged.get("type") or it.get("type") or "content").lower()
            r_raw = merged.get("rating")
            rating_out = (
                str(r_raw).strip()
                if r_raw is not None and str(r_raw).strip()
                else None
            )
            banners.append({
                "id": merged.get("id") or it["id"],
                "title": merged.get("title") or "Untitled",
                "type": rt_str,
                "image": img,
                "backdrop": backdrop,
                "description": desc[:220] + ("…" if len(desc) > 220 else ""),
                "genres": genres,
                "languages": langs,
                "rating": rating_out,
            })

        if banners:
            return banners, None

        # Posters only (root failed for every candidate)
        seen2: set[str] = set()
        out2: list[dict] = []
        for query in self._BANNER_SEARCH_QUERIES:
            items, err = self.search(query)
            if err:
                last_err = err
            for it in items:
                cid = it.get("id")
                if not cid or cid in seen2:
                    continue
                img = (it.get("image") or "").strip()
                if not img:
                    continue
                seen2.add(cid)
                desc = (it.get("description") or "").strip()
                r2 = it.get("rating")
                out2.append({
                    "id": cid,
                    "title": it.get("title") or "Untitled",
                    "type": (it.get("type") or "").lower() or "content",
                    "image": img,
                    "backdrop": img,
                    "description": desc[:220] + ("…" if len(desc) > 220 else ""),
                    "genres": [],
                    "languages": [],
                    "rating": str(r2).strip()
                    if r2 is not None and str(r2).strip()
                    else None,
                })
                if len(out2) >= cap:
                    return out2, None
        if not out2:
            return [], last_err
        return out2, None

    # Homepage category rails: MX search ``sections`` often only fill the first tab,
    # so each shelf runs its own query (curated labels for UX, not MX taxonomy).
    _HOME_SHELVES: tuple[tuple[str, str, str], ...] = (
        ("trending", "Trending now", "trending hindi web series"),
        ("movies", "Popular movies", "latest hindi movies"),
        ("shows", "Web series", "popular web series india"),
        ("global", "Global drama", "korean drama hindi dubbed"),
        ("reality", "Reality & music", "reality show hindi"),
        ("classics", "Timeless picks", "classic hindi cinema"),
    )

    def fetch_home_shelves(self, per_shelf: int = 14) -> tuple[list[dict], str | None]:
        """Returns ``[{id, title, items: [{id, title, type, image}]}]``."""
        cap = max(4, min(int(per_shelf), 24))
        shelves: list[dict] = []
        last_err: str | None = None

        for sid, stitle, query in self._HOME_SHELVES:
            items, err = self.search(query)
            if err:
                last_err = err
            row: list[dict] = []
            seen: set[str] = set()
            for it in items:
                cid = it.get("id")
                if not cid or cid in seen:
                    continue
                img = (it.get("image") or "").strip()
                if not img:
                    continue
                seen.add(cid)
                row.append({
                    "id": cid,
                    "title": it.get("title") or "Untitled",
                    "type": (it.get("type") or "").lower() or "content",
                    "image": img,
                })
                if len(row) >= cap:
                    break
            if row:
                shelves.append({"id": sid, "title": stitle, "items": row})

        if shelves:
            return shelves, None
        return [], last_err or "No catalog rows returned."

    def find_parsed_item_by_id(self, content_id: str, ref_title: str) -> dict | None:
        """Match a search hit by id when ``/detail/collection`` rejects the same id."""
        q = (ref_title or "").strip()
        if len(q) < 2:
            return None
        items, _ = self.search(q)
        for it in items:
            if it.get("id") == content_id:
                return it
        return None

    # ── Show / Movie Detail ────────────────────────────────

    def _get_collection_once(
        self, content_id: str, content_type: str
    ) -> tuple[dict | None, str | None]:
        """Single GET /detail/collection. On success with a full item, (detail, None)."""
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

    def get_collection(
        self, content_id: str, content_type: str = "tvshow"
    ) -> tuple[dict | None, str | None]:
        """Returns (detail_dict, error_message).

        MX ``detail/collection`` does not resolve episode IDs; use ``season_id`` +
        ``get_episodes`` in the stream router. For non-episode fallbacks we try
        ``movie`` / ``video`` without calling ``type=episode`` (avoids 400 noise).
        """
        t = (content_type or "tvshow").lower()
        if t == "episode":
            chain = ["movie", "video"]
        elif t == "movie":
            # Search often tags films as ``movie``; MX detail frequently expects ``video``.
            chain = ["movie", "video"]
        elif t == "video":
            chain = ["video", "movie"]
        else:
            chain = [content_type]

        last_error: str | None = None
        for ct in chain:
            detail, err = self._get_collection_once(content_id, ct)
            if detail:
                return detail, None
            if err:
                last_error = err
        return None, last_error

    def get_episode_collection_detail(self, content_id: str) -> dict | None:
        """Full episode row from ``detail/collection?type=episode`` (works when tab list is sparse)."""
        cid = (content_id or "").strip()
        if not cid:
            return None
        detail, _ = self._get_collection_once(cid, "episode")
        if isinstance(detail, dict) and detail.get("id") and detail.get("title"):
            return detail
        return None

    def episode_collection_stream_options(self, content_id: str) -> dict[str, str]:
        """Full HLS/DASH ladder from ``detail/collection?type=episode``.

        Season tab items often include only ``high``; episode detail usually lists
        ``high`` / ``main`` / ``base`` when available.
        """
        cid = (content_id or "").strip()
        if not cid:
            return {}
        detail, _ = self._get_collection_once(cid, "episode")
        if not isinstance(detail, dict):
            return {}
        stream = detail.get("stream")
        if not isinstance(stream, dict):
            return {}
        return parse_stream_options(stream)

    # ── Episodes ───────────────────────────────────────────

    def get_episodes(self, season_id: str) -> tuple[list[dict], str | None]:
        """Returns (episodes, error_message).

        MX returns ``next`` as ``finalId=…&pageDirection=1``; those must be sent as
        **separate** query params. A single ``next=…`` string repeats the first page.
        """
        url = f"{API_BASE}/detail/tab/tvshowepisodes"
        params: dict[str, str] = self._params({
            "type": "season",
            "id": season_id,
            "sortOrder": "0",
        })
        all_episodes: list[dict] = []
        seen_ids: set[str] = set()
        max_pages = 30
        try:
            for _ in range(max_pages):
                r = self._s.get(url, params=params, timeout=15)
                r.raise_for_status()
                data = r.json()
                raw_items = data.get("items") or []
                if not raw_items:
                    break
                new_count = 0
                for item in raw_items:
                    parsed = parse_item(item)
                    if parsed and parsed["id"] not in seen_ids:
                        seen_ids.add(parsed["id"])
                        all_episodes.append(parsed)
                        new_count += 1
                nxt = data.get("next")
                if not nxt or not isinstance(nxt, str) or not nxt.strip():
                    break
                q = urllib.parse.parse_qs(nxt.strip(), keep_blank_values=True)
                fid_list = q.get("finalId") or []
                pd_list = q.get("pageDirection") or []
                final_id = fid_list[0] if fid_list else None
                if not final_id:
                    break
                page_dir = (pd_list[0] if pd_list else "") or "1"
                params.pop("next", None)
                params["finalId"] = final_id
                params["pageDirection"] = str(page_dir)
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
#  URL helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _ids_from_url(url: str) -> list[str]:
    return re.findall(r"[a-f0-9]{24,}", url)


def _name_from_url(url: str) -> str:
    for part in url.rstrip("/").split("/"):
        if "watch-" in part:
            clean = re.sub(
                r"-(online|free|full|hd|episodes?|season|all)\b",
                "",
                part.replace("watch-", ""),
            )
            return clean.replace("-", " ").strip()
    return ""


def name_from_url(url: str) -> str:
    """Public helper for URL slug titles (browser extract fallback)."""
    return _name_from_url(url)
