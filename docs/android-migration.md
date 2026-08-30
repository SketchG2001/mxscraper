# Android migration notes

Branch: `android` (from `player`).

This document records the Phase 1 baseline. It is not a redesign.

## Current architecture

```text
React (Vite)  →  FastAPI  →  MX Player HTTP API
                     ├── /health, /api/search, /api/banners, /api/home/shelves
                     ├── /api/resolve, /api/content/*, /api/seasons/*/episodes
                     ├── /api/stream/*
                     ├── /api/extract-browser  (Selenium / Chrome, desktop)
                     └── HLS CORS proxy :8513
```

The scraper lives in `backend/services/mx_api.py`. Routers are a thin HTTP layer. The React app in `frontend/` is the UI.

## Phase 1 scope

Stabilized and tested the existing Python/FastAPI backend. No Android runtime, Capacitor, yt-dlp, FFmpeg, download pipeline, Selenium replacement, or Auth0 change.

## What remains desktop-only

- Selenium + ChromeDriver (`backend/services/browser_extract.py`)
- HLS proxy in-memory body buffering (web bind `0.0.0.0`; Android sets `PROXY_BIND_HOST=127.0.0.1`)
- `build.sh` (Ubuntu packages, system ffmpeg, chromedriver)
- Auth0 was removed; `/api/stream` and `/api/downloads` are public

## Selenium status

**Desktop-only web fallback. Do not remove. Do not port to Android in this phase.**

Normal catalog playback uses `MXPlayerAPI` over HTTP. Selenium runs only when a user hits `POST /api/extract-browser` (header “Extract via browser”). Replacement investigation is a later phase.

## FFmpeg status

Not used by the `player`/`android` FastAPI app. `bin/ffmpeg` and `bin/ffprobe` in git are Linux AArch64 ELF binaries (~86MB each), not Android Bionic. Do not bundle them into an APK as-is.

## yt-dlp status

Not a dependency on this branch. Download behavior exists only on `main` (`downloader.py`, Streamlit). Recovery belongs to a later phase.

## Phase 2 scope

Capacitor Android shell around the existing React Vite build. No Python on device, no downloads, no Auth0 redesign.

```text
npm run build   →  frontend/dist/
npx cap sync    →  frontend/android/
```

- App ID: `com.mxscraper.app`
- App name: `MX Scraper`
- Web dir: `dist` (bundled assets, no `server.url`)
- Permission: `INTERNET` only (Capacitor default)
- Routing: existing `BrowserRouter` (Capacitor Android origin is `https://localhost`)

### Same-origin / API (Phase 3)

Web + empty `VITE_API_BASE_URL` uses same-origin (`/api`, Vite proxy). The APK WebView origin is `https://localhost`. Android uses `frontend/src/lib/androidLocalApi.json` → `http://127.0.0.1:8787`. That JSON is the single port/host source; Gradle copies it into `BuildConfig`.

### Assets

- CSS, JS, `public/` files, Video.js CSS ship in `dist/`
- Google Fonts (`Outfit`) still load from fonts.googleapis.com — need network, or bundle later
- AdSense stays env-gated (off unless `VITE_ADSENSE_*` is set at build)

### localStorage

Watch progress still uses `localStorage`. Do not switch to Capacitor Preferences unless a device test shows it fails.

## Phase 3 scope

Embedded Python (Chaquopy 17.0.0, app Python **3.12**) starts the **existing** FastAPI app on `127.0.0.1:8787`. No second backend. Selenium is not on device. yt-dlp is a Phase 4 pip pin; FFmpeg is located at runtime, not the repo Linux `bin/` pair.

Android pip uses **pydantic 1.10.24** (pure Python). pydantic 2 requires `pydantic-core`, which has no official Android wheel on PyPI or Chaquopy’s index. FastAPI on device is therefore pinned `<0.128`. Desktop/web stays on pydantic 2.

```text
React → Capacitor WebView (https://localhost)
     → http://127.0.0.1:8787
     → Chaquopy + uvicorn
     → backend/main.py (same routers + MXPlayerAPI)
     → MX HTTPS API
```

- Bind: `127.0.0.1` only (not `0.0.0.0`)
- CORS on Android: `https://localhost`, `http://localhost`, credentials off
- CORS on web: unchanged `*` + credentials
- Cleartext: `network_security_config.xml` loopback only (not global `usesCleartextTraffic`)
- Pip set: `frontend/android/app/chaquopy-requirements.txt` (not `backend/requirements.txt`)
- Bootstrap: `android_server.py` + `LocalApiServer.java` (no MX logic)
- React waits on `/health` before catalog routes; failure uses the existing error banner
- HLS proxy bind on Android: `127.0.0.1` via `PROXY_BIND_HOST` (proxy itself is not redesigned)
- `/api/stream` and `/api/downloads` are public (Auth0 removed)
- Selenium stays lazy-imported in `browser_extract.py`; not installed on Android

### Phase 3 / 6 build notes

Debug APK builds with Chaquopy 17, Python 3.12, pydantic 1.10.24. Capacitor 8 needs **JDK 21** (`invalid source release: 21` on JDK 17). Session `JAVA_HOME` example: `C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot`. Host `buildPython` is `py -3.12`. APK size (debug, arm64 + x86_64): about 47 MB.

Device install was not completed: the Redmi Note 14 5G appears as a WPD device but `adb devices` is empty.

## Phase 4 scope

Download pipeline reuses `resolve_stream_response` (same as `/api/stream`). yt-dlp Python API. One in-memory job. App-private storage. Auth0 not weakened.

```text
React → POST /api/downloads
     → existing MXPlayerAPI stream resolution
     → DownloadManager (thread)
     → yt-dlp.YoutubeDL
     → FFmpeg remux (-c copy)
     → app-private files
```

FFmpeg strategy and license: `docs/ffmpeg-android.md`. Repo `bin/ffmpeg` is **not** used.

### Phase 4 not verified on device

No Android FFmpeg binary was built or executed here. Downloads return 503 until `libffmpeg.so` exists and `ffmpeg -version` succeeds.

## Phase 5 scope

Validation and hardening. No Media3, Auth0 redesign, Selenium port, or foreground service.

Code-level HLS fix (web unchanged): Capacitor is `https://localhost` and has no nginx `/hls/` path. Android now uses `http://127.0.0.1:<proxy_port>/…` (proxy binds IPv4 loopback). `allowMixedContent` is enabled so the WebView can reach that loopback HTTP endpoint; OS cleartext is still loopback-only.

Device/APK execution was **not** available in this environment (no JDK, SDK, or adb). Do not treat playback as proven.

## Phase 10 — Production hardening + release APK (2026-08-30)

### Build environment
- JDK 21 (Microsoft OpenJDK 21.0.12)
- Android SDK compile/target 36, build-tools 36
- Gradle 8.14.3 / AGP 8.13.0
- Capacitor 8.5.0 + Chaquopy 17.0.0 (Python 3.12)
- Device: motorola moto g54 5G, Android 15 (API 35), adb `ZD222G2YGZ`

### Hardening applied
- Removed duplicate `createRoot` mount in `frontend/src/main.tsx` (was double-mounting the SPA)
- Cached `ffmpeg_status()` so `/health` does not spawn `ffmpeg -version` every poll
- `android:allowBackup="false"`
- Keystore patterns enabled in `frontend/android/.gitignore`
- Release signingConfig: Play keystore via `MX_RELEASE_*` properties, else debug keystore for local sideload
- Throttled Android health-wait log spam; removed startup `console.info`

### APK build result
| Artifact | Path | Size |
| --- | --- | --- |
| Release | `frontend/android/app/build/outputs/apk/release/app-release.apk` | ~45.78 MB |
| Debug | `frontend/android/app/build/outputs/apk/debug/app-debug.apk` | ~47.74 MB |
| AAB | Not generated | — |

### Device test results (Phase 10)
| Check | Result |
| --- | --- |
| Release install + launch | PASS |
| Python / uvicorn / `/health` | PASS (`ffmpeg: unavailable`) |
| Search API | PASS |
| Debug SPA (single `#root`) | PASS |
| Home header + bottom nav | PASS |
| Playback + seek | PASS |
| Fullscreen → landscape → exit → portrait | PASS |
| Background / foreground + health | PASS |
| Downloads | BLOCKED — no `libffmpeg.so` |
| Auth0 | N/A — removed on this branch |
| Release WebView CDP | NOT AVAILABLE (non-debuggable); player matrix run on debug APK |

### Known limitations / release blockers
1. Play Store signing requires a real keystore (`MX_RELEASE_STORE_FILE` etc.); current release APK uses debug key when unset (sideload only).
2. Android FFmpeg binary not shipped — downloads stay unavailable.
3. Auth0 / `require_auth` not present — stream and downloads are public on loopback by design.
4. See also `docs/android-production-checklist.md`.

### Checklist
Full matrix: `docs/android-production-checklist.md`.

## Phase 11 — QA / release readiness (2026-08-30)

Audit: `docs/phase-11-audit.md`. Result: `docs/phase-11-result.md`. Release ops: `docs/android-release.md`.

Minimal fixes only (API fail banner text, meta copy, FileProvider scope, download path containment, lint NewApi/v27 styles, gitignore `.ffmpeg-build/`). No architecture change. Device smoke on moto g54 5G: health/search/play/fullscreen/BG **PASS**. Downloads still **BLOCKED** without FFmpeg. Play Store signing still **BLOCKED** without `MX_RELEASE_*`.

## Android blockers (remaining)

1. Play Store release keystore not provisioned
2. Android FFmpeg binary not built (`libffmpeg.so`)
3. Auth0 removed — stream/download open on loopback
4. HLS proxy remains a buffering relay (loopback-bound on Android)
5. pydantic-core has no official Android wheel; APK uses pydantic 1.10 + Python 3.12
6. Process-scoped downloads die if Android kills the app

## Configuration notes (not changed)

- `DEFAULT_PARAMS["platform"]` is `com.mxplay.desktop`
- User-Agent list is desktop browsers
- `/api/stream` is public (Auth0 removed)
- Settings load `.env` from the process cwd (expected: `backend/`)
- CORS is `allow_origins=["*"]` with `allow_credentials=True` on web; Android runtime uses localhost origins only

## Proxy notes (not changed)

- Full response buffered (`stream=False`)
- TLS `verify=False` fallback on SSLError
- Listens on `0.0.0.0`
- Accepts any `http(s)` target URL (open relay)

These are later-phase work.

## Future improvements (out of Phase 1)

- Local/Android auth for `/api/stream` without weakening web Auth0
- Streaming HLS proxy on loopback, with URL allowlisting
- Sync `requests` inside `async def` (do not rewrite until measured)
- `strip_stream_fields` is shallow; routers pass flat `parse_item` dicts
- `optional_auth` is unused
- Home banners/shelves do N+1 MX searches (battery cost on device)

## Later phase boundaries

| Phase | Intent |
| --- | --- |
| 2 | Capacitor + Android shell (this phase) |
| 3 | Embed Python; same `/api` contracts on device localhost (this phase) |
| 4 | Android FFmpeg + yt-dlp downloads (this phase; FFmpeg binary not shipped) |
| 5 | Android runtime / stream / download validation (this phase; device NOT TESTED) |
| 6 | Web Auth0 vs device-local auth |
| 7 | Video.js WebView validation |
| 8 | Packaging, storage, battery, size |
