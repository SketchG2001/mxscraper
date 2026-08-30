# APK build utility — result

Date: 2026-08-30. **No git commit.**

## Environment

| Tool | Value |
|------|--------|
| Node | v24.18.0 |
| npm | 11.16.0 |
| Java | JDK 21 (Microsoft) via `JAVA_HOME` |
| Android SDK | `%LOCALAPPDATA%\Android\Sdk` |
| Gradle | Wrapper 8.14.3 (`assembleDebug`) |
| Shell | Git Bash |

## Build

| Step | Result |
|------|--------|
| `./scripts/build-apk.sh --help` | **PASS** |
| bash `-n` syntax | **PASS** |
| frontend `npm run build` | **PASS** |
| `npx cap sync android` | **PASS** |
| `gradlew.bat :app:assembleDebug` | **PASS** |
| APK generated | **PASS** |

## APK

| Item | Value |
|------|--------|
| Path | `release/MX-Scraper.apk` (was `MX-Scraper-debug.apk`; renamed for sharing) |
| Size | **47.74 MB** (50060905 bytes) |
| SHA-256 | `29027a6e7088f1466afdd93e7deb04ba74f148ea3aad350c933d6fe6775b9218` |
| Type | DEBUG (not Play Store) |

## Device installation

| Check | Result |
|-------|--------|
| `adb install -r release/MX-Scraper.apk` | **PASS** (moto g54 5G; same debug-signed binary) |
| Launch + `/health` | **PASS** |

## Application runtime

**PASS** — cold launch after install; `MxLocalApi` ready; `/health` returned `status: ok`.

## Files changed

| File | Action |
|------|--------|
| `scripts/build-apk.sh` | **ADDED** |
| `docs/build-apk.md` | **ADDED** |
| `docs/phase-apk-build-result.md` | **ADDED** |
| `.gitignore` | **MODIFIED** (allowlist `/release/` despite VS `[Rr]elease/`) |

No application / Android / backend source changes.
