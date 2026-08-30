# Build a shareable DEBUG APK

Generate `release/MX-Scraper.apk` for manual distribution (WhatsApp, Telegram, Drive, GitHub Releases, etc.).

Internally this uses Android’s **debug** build type (`assembleDebug`) so it installs without a Play Store signing key. The filename is plain so recipients don’t think the app is unfinished.

This is **not** a Play Store release. Signing credentials are not involved.

## Requirements

- Node.js + npm
- JDK 21+ (Android Studio’s bundled JBR is fine)
- Android SDK (`ANDROID_HOME` or `ANDROID_SDK_ROOT`)
- Android project at `frontend/android` (Capacitor)

## Setup

```bash
# Examples — use your actual paths
export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"   # Git Bash
export ANDROID_HOME="/c/Users/YOU/AppData/Local/Android/Sdk"
```

On Windows PowerShell (before opening Git Bash, or export inside Bash):

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
```

Leave `VITE_API_BASE_URL` unset for APK builds. Native Android uses `frontend/src/lib/androidLocalApi.json` (`http://127.0.0.1:8787`).

## Build

From the repository root (Git Bash or WSL):

```bash
./scripts/build-apk.sh
```

Clean frontend `dist` + Gradle clean, then rebuild:

```bash
./scripts/build-apk.sh --clean
```

Help:

```bash
./scripts/build-apk.sh --help
```

## Pipeline

```text
npm run build          → frontend/dist
npx cap sync android   → Capacitor copies assets
gradlew assembleDebug  → app-debug.apk
copy                   → release/MX-Scraper.apk
```

## Output

| Item | Value |
|------|--------|
| Path | `release/MX-Scraper.apk` |
| Build type | debug-signed (sideload; not Play Store) |
| Checksum | SHA-256 printed on success |

The `release/` directory is gitignored.

## Optional install

```bash
adb install -r release/MX-Scraper.apk
adb shell am start -n com.mxscraper.app/.MainActivity
```

Installation is optional; the script succeeds when the APK file is produced.
