# Android production readiness checklist

Branch: `android`. Phase 10 audit. Status values: **PASS** | **FAIL** | **NOT TESTED** | **BLOCKED**.

Device claims require a physical install; do not infer from source alone.

## Build

| Item | Status | Notes |
|------|--------|-------|
| `npm run build` | PASS / re-run in Phase 10 | Vite + `tsc` |
| `npm run cap:sync` | PASS / re-run | Bundles `dist/` into Android assets; no `server.url` |
| `assembleDebug` | PASS / re-run | Validated prior + this phase |
| `assembleRelease` | PASS | ~45.78 MB; signed with debug keystore when `MX_RELEASE_*` unset |
| Toolchain pin | PASS | JDK 21, AGP 8.13.0, Gradle 8.14.3, Capacitor 8.5, Chaquopy 17, Python 3.12 |

## Android configuration

| Item | Status | Notes |
|------|--------|-------|
| `applicationId` | PASS | `com.mxscraper.app` |
| minSdk 24 / targetSdk 36 / compileSdk 36 | PASS | `variables.gradle` |
| `INTERNET` only | PASS | No storage/camera/location/FGS |
| Cleartext | PASS | Loopback domains only in `network_security_config.xml` |
| `allowBackup` | PASS | Set `false` in Phase 10 |
| No `server.url` | PASS | Capacitor loads local `dist/` |
| Keystore gitignore | PASS | `*.jks` / `*.keystore` enabled Phase 10 |

## Frontend

| Item | Status | Notes |
|------|--------|-------|
| Single API client | PASS | `frontend/src/lib/api.ts` |
| Android API base SSOT | PASS | `androidLocalApi.json` → `apiBase` + `BuildConfig` |
| Double React mount | PASS | Removed duplicate `createRoot` in Phase 10 |
| Health gate UX | PASS | Banner on fail; no blank shell |
| Console spam | PASS | Startup `console.info` removed; errors kept |

## Backend

| Item | Status | Notes |
|------|--------|-------|
| Bind `127.0.0.1` on Android | PASS | `android_server.py` |
| One uvicorn | PASS | `LocalApiServer` `started` guard |
| `/health` lightweight | PASS | FFmpeg status cached after first check |
| No Selenium on device | PASS | Not in Chaquopy pip set |
| pytest | PASS / re-run | |

## Authentication

| Item | Status | Notes |
|------|--------|-------|
| Auth0 on Android SPA | BLOCKED / N/A | Removed earlier; `AuthGate` is Router only |
| `require_auth` on stream/download | BLOCKED / N/A | Endpoints public by design on this branch |
| Loopback exposure | PASS | Not bound to `0.0.0.0` |

## Streaming

| Item | Status | Notes |
|------|--------|-------|
| Stream via MXPlayerAPI | PASS | No client-supplied media URL |
| HLS via loopback proxy | PASS | `PROXY_BIND_HOST=127.0.0.1` |
| Mixed content scoped | PASS | Capacitor `allowMixedContent` + NSC loopback |

## Player

| Item | Status | Notes |
|------|--------|-------|
| Video.js only | PASS | No Media3 |
| Dispose / listeners | PASS | Code review; device retest Phase 10 |
| Fullscreen / landscape | PASS | Device-proven Phase 8; retest Phase 10 |
| Center play vs seek | PASS | Fixed Phase 8 |

## Downloads

| Item | Status | Notes |
|------|--------|-------|
| content_id → resolve → yt-dlp | PASS | No `url=` download API |
| Path / filename sanitization | PASS | Existing services |
| One active job | PASS | In-memory manager |
| End-to-end download | BLOCKED | No `libffmpeg.so` in jniLibs |

## FFmpeg

| Item | Status | Notes |
|------|--------|-------|
| Locator uses jniLibs | PASS | `libffmpeg.so` path |
| Binary present | BLOCKED | `jniLibs/arm64-v8a/` README only |
| Repo `bin/ffmpeg` blocked | PASS | Explicit blocklist |

## Python / Chaquopy

| Item | Status | Notes |
|------|--------|-------|
| Startup path | PASS | MxApplication → LocalApiServer → android_server |
| pydantic 1.10 on device | PASS | Documented constraint |

## Navigation

| Item | Status | Notes |
|------|--------|-------|
| Single `__mxConsumeBack` | PASS | MainActivity → Layout |
| FS / menu / resume priority | PASS | Player chrome + MxVideoPlayer |

## Lifecycle

| Item | Status | Notes |
|------|--------|-------|
| Background / foreground | PASS | Phase 8 |
| Process death relaunch | PASS | Phase 8 |
| Health poll finite | PASS | Java 120 attempts; SPA 30s then banner+retry |

## Security

| Item | Status | Notes |
|------|--------|-------|
| Secrets in git | PASS | `.env` ignored; no tracked secrets found |
| Download URL injection | PASS | Not accepted |
| Storage | PASS | App-private downloads; backup off |

## Storage

| Item | Status | Notes |
|------|--------|-------|
| App-private downloads | PASS | `filesDir/downloads` |
| watchProgress localStorage | PASS | |

## Logging

| Item | Status | Notes |
|------|--------|-------|
| Health wait spam | PASS | Throttled in Phase 10 |
| Production errors retained | PASS | |

## Performance

| Item | Status | Notes |
|------|--------|-------|
| Cold start to health | PASS | ~2s on moto g54 (Phase 8) |
| Premature optimization | PASS | None applied |

## APK release

| Item | Status | Notes |
|------|--------|-------|
| Release APK generated | PASS | `app-release.apk` ~45.78 MB |
| Play Store signing | BLOCKED | Needs real keystore (`MX_RELEASE_*`) |
| AAB | NOT TESTED | Not required for sideload |

## Device testing

| Item | Status | Notes |
|------|--------|-------|
| Physical device | PASS | moto g54 5G / Android 15 |
| Catalog / stream / FS | PASS | Debug APK CDP; release install/health/search PASS |
| Downloads | BLOCKED | FFmpeg |

## Release blockers (honest)

1. **Play Store signing keystore** not provisioned → sideload release only with debug key.
2. **FFmpeg `libffmpeg.so` missing** → downloads remain unavailable (expected UI).
3. **Auth0 removed** → if product requires authenticated stream/download, that is a separate phase (not reintroduced here).
