#!/usr/bin/env bash
# MX Scraper — build a shareable APK for manual distribution.
# Usage: ./scripts/build-apk.sh [--clean] [--help]
#
# Output: release/MX-Scraper.apk
# Internally uses Gradle assembleDebug (debug-signed sideload). Not Play Store.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
ANDROID="$FRONTEND/android"
OUT_DIR="$ROOT/release"
OUT_APK="$OUT_DIR/MX-Scraper.apk"
CLEAN=0

die() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
MX Scraper APK Builder

Usage:
  ./scripts/build-apk.sh
  ./scripts/build-apk.sh --clean
  ./scripts/build-apk.sh --help

Options:
  --clean    Clean frontend/dist and Android build outputs
  --help     Show this help message

Output:
  release/MX-Scraper.apk

Shareable sideload APK (WhatsApp, Drive, GitHub Releases, etc.).
Built with assembleDebug (debug keystore) — not a Play Store release.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --help|-h) usage; exit 0 ;;
    --clean) CLEAN=1 ;;
    *) die "Unknown option: $arg (try --help)" ;;
  esac
done

is_windows() {
  case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

check_node() {
  command -v node >/dev/null 2>&1 || die "Node.js was not found."
  command -v npm >/dev/null 2>&1 || die "npm was not found."
  echo "  Node: $(node -v)"
  echo "  npm:  $(npm -v)"
}

check_java() {
  local java_bin=""
  if [ -n "${JAVA_HOME:-}" ]; then
    if is_windows && [ -x "$JAVA_HOME/bin/java.exe" ]; then
      java_bin="$JAVA_HOME/bin/java.exe"
    elif [ -x "$JAVA_HOME/bin/java" ]; then
      java_bin="$JAVA_HOME/bin/java"
    else
      die "JAVA_HOME is set ($JAVA_HOME) but bin/java was not found."
    fi
  elif command -v java >/dev/null 2>&1; then
    java_bin="$(command -v java)"
  else
    die "Java/JDK is required to build the Android APK.
Set JAVA_HOME to a JDK 21+ install (Android Studio's bundled JBR works), or add java to PATH."
  fi
  echo "  Java: $("$java_bin" -version 2>&1 | head -n 1)"
  if [ -n "${JAVA_HOME:-}" ]; then
    echo "  JAVA_HOME=$JAVA_HOME"
  fi
}

check_android_sdk() {
  local sdk=""
  if [ -n "${ANDROID_HOME:-}" ]; then
    sdk="$ANDROID_HOME"
  elif [ -n "${ANDROID_SDK_ROOT:-}" ]; then
    sdk="$ANDROID_SDK_ROOT"
  else
    die "Android SDK was not found.
Set ANDROID_HOME or ANDROID_SDK_ROOT to your SDK directory
(e.g. the path shown in Android Studio → Settings → Android SDK)."
  fi
  [ -d "$sdk" ] || die "Android SDK path does not exist: $sdk"
  # Prefer ANDROID_HOME for Gradle conventions.
  export ANDROID_HOME="$sdk"
  export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$sdk}"
  echo "  ANDROID_HOME=$ANDROID_HOME"
}

apk_sha256() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  elif is_windows && command -v certutil.exe >/dev/null 2>&1; then
    # certutil prints "Hash of file:" then the hash on the next line(s).
    certutil.exe -hashfile "$(cygpath -w "$file" 2>/dev/null || echo "$file")" SHA256 2>/dev/null \
      | tr -d '\r' \
      | awk 'NR==2 { gsub(/ /,"",$0); print; exit }'
  else
    echo ""
  fi
}

echo "[1/7] Checking environment"
[ -d "$FRONTEND" ] || die "frontend/ not found under $ROOT"
[ -f "$FRONTEND/package.json" ] || die "frontend/package.json not found."
[ -d "$ANDROID" ] || die "Android project not found at frontend/android."
if is_windows; then
  [ -f "$ANDROID/gradlew.bat" ] || die "Gradle wrapper not found (gradlew.bat)."
else
  [ -f "$ANDROID/gradlew" ] || die "Gradle wrapper not found (gradlew)."
fi
check_node
check_java
check_android_sdk

# Android APK must keep loopback API (androidLocalApi.json). Do not set VITE_API_BASE_URL.
unset VITE_API_BASE_URL || true
echo "  VITE_API_BASE_URL unset (Android uses 127.0.0.1 via androidLocalApi.json)"

cd "$FRONTEND"

if [ "$CLEAN" -eq 1 ]; then
  echo "[clean] Removing frontend/dist and running Gradle clean"
  rm -rf "$FRONTEND/dist"
  cd "$ANDROID"
  if is_windows; then
    cmd.exe //c "gradlew.bat clean" || die "Gradle clean failed."
  else
    ./gradlew clean || die "Gradle clean failed."
  fi
  cd "$FRONTEND"
fi

echo "[2/7] Installing frontend dependencies"
if [ ! -d node_modules ]; then
  if [ -f package-lock.json ]; then
    npm ci || die "npm ci failed."
  else
    npm install || die "npm install failed."
  fi
else
  echo "  node_modules present; skipping install"
fi

echo "[3/7] Building frontend"
npm run build || die "Frontend build failed."

echo "[4/7] Syncing Capacitor"
npx cap sync android || die "Capacitor sync failed."

echo "[5/7] Building Android APK"
cd "$ANDROID"
if is_windows; then
  cmd.exe //c "gradlew.bat :app:assembleDebug" || die "Android APK build failed."
else
  ./gradlew :app:assembleDebug || die "Android APK build failed."
fi

SRC_APK="$ANDROID/app/build/outputs/apk/debug/app-debug.apk"
[ -f "$SRC_APK" ] || die "APK output could not be located (expected $SRC_APK)."

echo "[6/7] Copying APK"
mkdir -p "$OUT_DIR"
cp -f "$SRC_APK" "$OUT_APK" || die "Failed to copy APK to $OUT_APK."

echo "[7/7] Verifying APK"
[ -s "$OUT_APK" ] || die "APK file is empty: $OUT_APK"

# Portable size in bytes
BYTES=$(wc -c < "$OUT_APK" | tr -d ' ')
# Approximate MB for humans
SIZE_MB=$(awk -v b="$BYTES" 'BEGIN { printf "%.2f", b/1024/1024 }')

HASH="$(apk_sha256 "$OUT_APK" || true)"

echo ""
echo "========================================"
echo "APK BUILD SUCCESSFUL"
echo "========================================"
echo ""
echo "APK:"
echo "  $OUT_APK"
echo ""
echo "Size:"
echo "  ${SIZE_MB} MB (${BYTES} bytes)"
echo ""
if [ -n "$HASH" ]; then
  echo "SHA-256:"
  echo "  $HASH"
else
  echo "WARNING: SHA-256 tool unavailable; checksum was not generated."
fi
echo ""
echo "The APK is ready to share (sideload; not Play Store)."
