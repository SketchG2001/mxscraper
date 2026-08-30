# Phase 11 — Production audit (read-only)

Branch: `android`. Date: 2026-08-30.  
Status markers used later in results: PASS | FAIL | NOT TESTED | BLOCKED.

This document records the audit **before** Phase 11 code changes. Phase 10 hardening was already present in the tree.

---

## 1. Current architecture

```text
React (Vite) + Capacitor WebView (https://localhost)
        │
        ▼
http://127.0.0.1:8787  ← Chaquopy Python 3.12 + uvicorn (android_server)
        │
        ├── FastAPI routers (search, content, stream, downloads, extract)
        ├── MXPlayerAPI (HTTPS to MX)
        └── HLS CORS proxy on 127.0.0.1:<proxy_port> (Android)

Playback: Video.js + VHS → loopback proxy → remote HLS
Downloads: content_id → resolve_stream → yt-dlp → FFmpeg (if libffmpeg.so present)
```

Web and Android share the same backend source (`chaquopy sourceSets` → `../../../backend`). Android uses a separate pip set (`chaquopy-requirements.txt`).

---

## 2. Android startup flow

```text
MxApplication.onCreate
  → PyApplication (Chaquopy)
  → filesDir/downloads mkdir
  → FfmpegLocator.ensure (copy native libffmpeg.so if present)
  → LocalApiServer.start(port from BuildConfig ← androidLocalApi.json)
       → thread: android_server.start → uvicorn 127.0.0.1:port
       → thread: poll GET /health (≤120 × 250ms)
MainActivity
  → Capacitor Bridge + WebView loads bundled dist/
  → OnBackPressed → window.__mxConsumeBack
```

`capacitor.config.ts`: no `server.url`; `allowMixedContent`; App back handler disabled; SystemBars CSS insets.

---

## 3. Python startup flow

`android_server.py` sets `ANDROID_RUNTIME`, `PROXY_BIND_HOST=127.0.0.1`, download/ffmpeg env, then imports `main:app` and runs uvicorn on **127.0.0.1 only**.  
Idempotent if `_server.started`. Process-scoped (not per Activity).

---

## 4. React startup flow

```text
main.tsx → single createRoot → QueryProvider → AuthGate(BrowserRouter) → App
App (Android): waitForHealth(30s) → ready | fail banner + slow retry
Routes mount only after ready (or non-Android skip)
```

Confirmed: **one** `createRoot` (Phase 10 fixed duplicate mount).

---

## 5. API communication

| Concern | Source of truth |
|---------|-----------------|
| Android host/port | `frontend/src/lib/androidLocalApi.json` |
| Frontend base URL | `apiBase.ts` → JSON on native; else `VITE_API_BASE_URL` / same-origin |
| Gradle BuildConfig | Parses same JSON |
| HTTP client | **Only** `frontend/src/lib/api.ts` |

---

## 6. Streaming flow

```text
WatchPage → fetchStream(content_id) → /api/stream/...
         → proxiedQualitySources(proxy_port) → Video.js src = http://127.0.0.1:proxy/...
Proxy: threaded HTTP server; rewrites m3u8; currently buffers full response bodies (stream=False)
```

---

## 7. Download flow

```text
POST /api/downloads { content_id, type, ... }  — no client media URL
  → resolve_stream_response (same as stream)
  → DownloadManager one job
  → yt-dlp → FFmpeg remux
  → app-private filesDir/downloads
```

Without `jniLibs/**/libffmpeg.so`: health reports `ffmpeg: unavailable`; API returns expected failure UX.

---

## 8. Authentication flow

**Auth0 removed on this branch.**  
`AuthGate` = `BrowserRouter` only. `backend/auth.py` deleted. Stream/download have **no** `require_auth`.  
Residual empty `auth0_*` settings in `config.py` are unused.  
If product requires authenticated APIs → **release blocker / separate phase**.

---

## 9. Navigation flow

```text
MainActivity back
  → __mxConsumeBack (Layout): search → mx-android-back → FS → VJS menu → history → min
Player mx-android-back: menu → next prompt → unlock → exit fullscreen
MxVideoPlayer: resume overlay → stream error → (non-cinema) VJS FS
```

Single history stack (React Router). No duplicate nav stack.

---

## 10. Lifecycle flow

| Event | Expected |
|-------|----------|
| Orientation / configChanges | Activity not recreated (manifest flags) |
| App background/foreground | Process + uvicorn typically survive |
| Process death | Python + in-memory download jobs lost; cold start again |
| Player unmount | dispose + listener/timer cleanup |

---

## 11. Storage flow

- Downloads: app-private `filesDir/downloads`
- Progress: `localStorage` (`watchProgress`)
- `allowBackup="false"`
- Permissions: `INTERNET` only

---

## 12. Potential memory leaks

| Item | Risk | Notes |
|------|------|-------|
| Duplicate React root | Mitigated | Fixed Phase 10 |
| Player timers/listeners | Low | `usePlayerControlsVisibility` + dispose path |
| HLS proxy full buffer | **Medium** | `stream=False` loads entire segment into RAM |
| React Query | Low | `staleTime` 60s, `retry` 1 |
| Download temps | Low | Cleanup on success/fail/cancel in manager |

---

## 13. Potential race conditions

| Item | Notes |
|------|-------|
| Health before uvicorn listen | Expected; poll until ready or timeout |
| Quality switch mid-play | Seek-after-load refs; dispose/recreate intentional |
| Double LocalApiServer.start | Guarded by `started` |

---

## 14. Potential crash points

| Item | Notes |
|------|-------|
| Python start failure | SPA fail banner + retry (not blank forever) |
| Missing FFmpeg | Soft fail for downloads |
| Stream errors | Player error UI + limited auto-retry |
| Release WebView CDP | N/A (non-debuggable) — not a user crash |

---

## 15. Security risks

| Risk | Severity | Mitigation / status |
|------|----------|---------------------|
| Open HLS proxy (any URL) | High on LAN bind | Android binds **127.0.0.1** |
| Proxy TLS verify=False fallback | Medium | Existing; do not expand |
| Public stream/download | Product | Loopback-only on device; Auth0 removed |
| Secrets in APK | Low | No tracked secrets found |
| Broad FileProvider `external-path` | Low | Provider not exported; downloads via API |
| Path traversal downloads | Low | Server-owned paths + filename sanitize |

---

## 16. Performance risks

- HLS full-body buffering (largest concern)
- Chaquopy + yt-dlp dominate APK size (~45–48 MB)
- Google Fonts network fetch (needs connectivity)

---

## 17. Release blockers

1. **Play Store keystore** — `MX_RELEASE_*` unset → debug-signed release (sideload only)
2. **`libffmpeg.so` missing** — downloads BLOCKED
3. **Auth0 / require_auth** — if authenticated APIs are required for ship

Non-blockers for sideload catalog/playback: already device-validated in Phase 8/10.

---

## Phase 11 recommended code scope

**Leave working systems alone.** Only apply confirmed, minimal fixes:

1. Surface `localApiFailed` message from App in Layout (UX inconsistency)
2. Fix misleading `index.html` auth copy if still present
3. Ignore `.ffmpeg-build/` in git so large FFmpeg tarballs are not committed

**Do not** rewrite HLS proxy, Auth0, player UI, or Media3 in this phase.
