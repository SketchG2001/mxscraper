# Phase 11 — Result

Date: 2026-08-30. Branch: `android`. **No git commit.**

## 1. What was audited

Full android-branch stack: Capacitor, Chaquopy, FastAPI, HLS proxy, Video.js player, downloads, Auth0 status, navigation/back, safe areas, Gradle/release signing, tests, git status/diff.  
Written up in `docs/phase-11-audit.md` before code changes.

## 2. What was changed

| Change | Why |
|--------|-----|
| Layout shows `localApiFailed` prop text | Confirmed UX bug: App passed a message Layout ignored |
| `index.html` meta dropped “Sign in for playback” | Auth0 removed; misleading copy |
| FileProvider paths → files/cache only | Confirmed hardening: no whole external storage |
| Download file serve path must stay under `downloads_root()` | Path-containment safety |
| `.gitignore` → `.ffmpeg-build/` | Prevent committing FFmpeg source tarball |
| `windowLightNavigationBar` → `values-v27` | Lint NewApi error (minSdk 24) |
| Manifest: permission before `<application>` | Lint ManifestOrder |
| Lint disable `PropertyEscape` for local.properties | Machine SDK path noise |

**Not changed:** player UI, Media3, Auth0, HLS proxy streaming rewrite, API contracts, Selenium, second API client.

## 3. Why each change was necessary

Only confirmed bugs / lint release blockers / small security containment. Working architecture left alone.

## 4–5. Tests executed / results

| Test | Result |
|------|--------|
| pytest | **PASS** (72) |
| `npm run build` / `tsc` | **PASS** |
| `npm run cap:sync` | **PASS** |
| `:app:lintDebug` | **PASS** (after fixes) |
| `:app:assembleDebug` | **PASS** |
| `:app:assembleRelease` | **PASS** |

## 6. APK build result

| Artifact | Size | Path |
|----------|------|------|
| Debug | ~47.74 MB | `frontend/android/app/build/outputs/apk/debug/app-debug.apk` |
| Release | ~45.78 MB | `frontend/android/app/build/outputs/apk/release/app-release.apk` |
| AAB | **NOT TESTED** | Not generated |

Release signing without `MX_RELEASE_*` uses debug keystore (sideload only).

## 7. Device test result

Device: **moto g54 5G**, Android **15**, adb `ZD222G2YGZ`.

| Check | Result |
|-------|--------|
| Install debug APK | **PASS** |
| Launch / Python / `/health` | **PASS** (`ffmpeg: unavailable`) |
| Search API | **PASS** |
| Home UI (header + bottom nav, 1 `#root`) | **PASS** |
| Play + fullscreen landscape + exit portrait | **PASS** |
| Background / foreground + health | **PASS** |
| Android 10–14 / multi-device matrix | **NOT TESTED** |
| 3-button nav vs gesture (explicit) | **NOT TESTED** (device uses gesture; no failure observed) |

## 8. Streaming test result

**PASS** on device (debug CDP): video `readyState=4`, play, fullscreen landscape fill, restore portrait.

## 9. Download test result

**BLOCKED** — no `libffmpeg.so` in jniLibs. UI/API correctly report unavailable. End-to-end download **NOT TESTED**.

## 10. Lifecycle test result

| Scenario | Result |
|----------|--------|
| Background while app alive | **PASS** (same PID, health 200) |
| Kill / relaunch | **PASS** (Phase 10; not re-force-stopped this pass beyond install) |
| Orientation via FS enter/exit | **PASS** |
| Background while downloading | **NOT TESTED** (FFmpeg blocked) |

## 11. Security findings

- No secrets in tracked sources found.
- Stream/download public on loopback (Auth0 removed) — product decision / blocker if auth required.
- Open HLS proxy mitigated on Android by `127.0.0.1` bind; still buffers full bodies.
- FileProvider narrowed; download file path checked against downloads root.
- TLS `verify=False` proxy fallback unchanged (existing).

## 12. Performance findings

- Largest risk remains HLS proxy full-buffer (`stream=False`) — **deferred** (not rewritten).
- FFmpeg `/health` remains cached (Phase 10).
- APK size dominated by Chaquopy/Python (~46 MB) — expected.

## 13. Remaining blockers

1. Play Store upload keystore (`MX_RELEASE_*`)
2. Ship `libffmpeg.so` for downloads
3. Auth0 / `require_auth` if product requires authenticated APIs

## 14. Known limitations

- No AAB in this phase
- Release APK non-debuggable (no CDP)
- In-memory download jobs die with process
- Web CORS still `*` (desktop); Android CORS localhost-only
- `.ffmpeg-build/ffmpeg-7.1.tar.xz` may exist locally; now gitignored

## 15. Release readiness

**BLOCKED** for Play Store / full product release (keystore + FFmpeg + optional Auth).

**Sideload catalog + playback:** validated on one Android 15 device; acceptable for internal QA builds only.

Docs: `docs/phase-11-audit.md`, `docs/android-release.md`, updated checklist/migration as needed.
