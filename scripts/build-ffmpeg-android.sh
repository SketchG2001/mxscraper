#!/usr/bin/env bash
# Cross-compile official FFmpeg (LGPL, remux-oriented) for Android arm64-v8a.
# Output: frontend/android/app/src/main/jniLibs/arm64-v8a/libffmpeg.so
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_ROOT="${FFMPEG_BUILD_ROOT:-$ROOT/.ffmpeg-build}"
NDK="${ANDROID_NDK_HOME:-${ANDROID_HOME:-$LOCALAPPDATA/Android/Sdk}/ndk/28.2.13676358}"
API=24
ARCH=aarch64
FFMPEG_VER="${FFMPEG_VER:-7.1}"
SRC="$BUILD_ROOT/ffmpeg-$FFMPEG_VER"
PREFIX="$BUILD_ROOT/install-android-arm64"
OUT_DIR="$ROOT/frontend/android/app/src/main/jniLibs/arm64-v8a"
HOST_TAG=windows-x86_64
TOOLCHAIN="$NDK/toolchains/llvm/prebuilt/$HOST_TAG"

if [[ ! -d "$TOOLCHAIN" ]]; then
  echo "NDK toolchain missing: $TOOLCHAIN" >&2
  exit 1
fi

export PATH="$TOOLCHAIN/bin:$PATH"
CC="$TOOLCHAIN/bin/${ARCH}-linux-android${API}-clang"
CXX="$TOOLCHAIN/bin/${ARCH}-linux-android${API}-clang++"

mkdir -p "$BUILD_ROOT" "$OUT_DIR"

if [[ ! -d "$SRC" ]]; then
  ARCHIVE="$BUILD_ROOT/ffmpeg-${FFMPEG_VER}.tar.xz"
  if [[ ! -f "$ARCHIVE" ]]; then
    echo "Missing $ARCHIVE — download ffmpeg-${FFMPEG_VER}.tar.xz first" >&2
    exit 1
  fi
  tar -xJf "$ARCHIVE" -C "$BUILD_ROOT"
fi

cd "$SRC"
# Clean prior configure if present
[[ -f ffbuild/config.mak ]] && make distclean || true

./configure \
  --prefix="$PREFIX" \
  --enable-cross-compile \
  --target-os=android \
  --arch=aarch64 \
  --cpu=armv8-a \
  --cc="$CC" \
  --cxx="$CXX" \
  --ld="$CC" \
  --ar=llvm-ar \
  --nm=llvm-nm \
  --ranlib=llvm-ranlib \
  --strip=llvm-strip \
  --extra-cflags="-O2 -fPIC -DANDROID" \
  --extra-ldflags="-lm -lc -Wl,-z,max-page-size=16384" \
  --disable-doc \
  --disable-htmlpages \
  --disable-manpages \
  --disable-podpages \
  --disable-txtpages \
  --disable-debug \
  --disable-ffplay \
  --disable-ffprobe \
  --disable-avdevice \
  --disable-postproc \
  --disable-network \
  --disable-gpl \
  --disable-nonfree \
  --disable-autodetect \
  --enable-static \
  --disable-shared \
  --enable-small \
  --disable-everything \
  --enable-avutil \
  --enable-avcodec \
  --enable-avformat \
  --enable-swresample \
  --enable-protocol=file,pipe,concat \
  --enable-demuxer=mpegts,mov,matroska,webm,aac,h264,hevc,m4v,rawvideo \
  --enable-muxer=mp4,ipod,mpegts,matroska \
  --enable-parser=h264,aac,hevc,mpeg4video,mpegaudio \
  --enable-bsf=aac_adtstoasc,h264_mp4toannexb,hevc_mp4toannexb,extract_extradata \
  --enable-decoder=h264,aac,hevc \
  --disable-encoders \
  --disable-filters \
  --enable-filter=aresample \
  --disable-iconv \
  --disable-zlib \
  --disable-xlib \
  --disable-libxcb \
  --disable-vaapi \
  --disable-vdpau

make -j"${NUMBER_OF_PROCESSORS:-4}"
make install

# Package CLI as libffmpeg.so for Android jniLibs packaging + FfmpegLocator.
cp -f "$PREFIX/bin/ffmpeg" "$OUT_DIR/libffmpeg.so"
# License texts for LGPL distribution obligations.
cp -f "$SRC/COPYING.LGPLv2.1" "$OUT_DIR/COPYING.LGPLv2.1" 2>/dev/null || \
  cp -f "$SRC/LICENSE.md" "$OUT_DIR/LICENSE.md" 2>/dev/null || true

echo "Built: $OUT_DIR/libffmpeg.so"
ls -la "$OUT_DIR/libffmpeg.so"
file "$OUT_DIR/libffmpeg.so" || true
"$PREFIX/bin/ffmpeg" -version | head -n 3 || true
