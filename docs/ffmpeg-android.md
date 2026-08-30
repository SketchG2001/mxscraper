# Android FFmpeg (Phase 4)

## Decision

FFmpeg is **not** bundled in this repository.

| Candidate | Verdict |
| --- | --- |
| `bin/ffmpeg`, `bin/ffprobe` | **Rejected** — Linux AArch64 ELF, not Android Bionic |
| Random GitHub “prebuilt Android ffmpeg” | **Rejected** — unverified provenance |
| Official FFmpeg source + Android NDK, LGPL | **Required** |

Official FFmpeg does not publish Android binaries. The only acceptable integration is a binary **you** cross-compile from [ffmpeg.org](https://ffmpeg.org/download.html) / [git.ffmpeg.org](https://git.ffmpeg.org/ffmpeg.git).

## License

Default FFmpeg is **LGPL 2.1 or later**.

This project must use a **pure LGPL** configure:

```text
--disable-gpl
--disable-nonfree
```

Do **not** enable x264, x265, or other GPL components. A GPL FFmpeg binary would impose GPL on the application.

LGPL obligations if you later ship `libffmpeg.so`:

- Include the FFmpeg license texts (`COPYING.LGPLv2.1` / `LICENSE.md` from the FFmpeg tree).
- State that FFmpeg is used and is LGPL.
- Provide the corresponding FFmpeg source (or a written offer) for the exact tag you built.
- Prefer a shared `libffmpeg.so` so users can replace the library.

Remux-only (`-c copy`) does not require GPL encoders.

## ABI

Ship **arm64-v8a** first (`aarch64-linux-android`).

x86_64 emulator support is optional. Phase 4 does not vendor an x86_64 binary.

minSdk for this app is 24. Target API 28+ for the NDK sysroot if your NDK requires it; keep the executable compatible with API 24 if possible.

## Build outline (not run in the Phase 4 agent environment)

This machine has no Android NDK. On a Linux host with NDK r26+ or r28:

```bash
# Official release tag, example:
# https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz

./configure \
  --prefix=./install-android \
  --disable-doc --disable-gpl --disable-nonfree \
  --enable-cross-compile --target-os=android --arch=aarch64 \
  --enable-small \
  --disable-everything \
  --enable-protocol=file,http,https,tcp,tls \
  --enable-demuxer=hls,mpegts,mov,mp4 \
  --enable-muxer=mp4,mpegts \
  --enable-parser=h264,aac,hevc \
  --enable-decoder=h264,aac,hevc \
  --enable-encoder=aac \
  --enable-filter=aresample \
  --enable-bsf=h264_mp4toannexb,aac_adtstoasc \
  --pkg-config-flags=--static

make -j"$(nproc)"
```

Install the resulting `ffmpeg` executable as:

```text
frontend/android/app/src/main/jniLibs/arm64-v8a/libffmpeg.so
```

Android packs `lib*.so` from `jniLibs` into `nativeLibraryDir`. `FfmpegLocator` copies that file to app-private storage, marks it executable, and runs `ffmpeg -version`.

Enable HTTPS only if you link a redistributable TLS stack permitted by your FFmpeg configure. yt-dlp can download over HTTPS with Python `requests`; FFmpeg is used for **mux/remux**, not as the HTTP client.

## Runtime

| Env | Locator |
| --- | --- |
| Android | `FFMPEG_PATH` from Java after `FfmpegLocator.ensure`, then `ANDROID_NATIVE_LIB_DIR/libffmpeg.so` |
| Web | `FFMPEG_PATH` only — no `which` / `where`, no `/usr/bin/ffmpeg` |

`GET /health` reports `"ffmpeg": "available" | "unavailable"`.

## Status (this environment)

- Strategy: documented
- Binary: **not built**
- Execution test: **not run**
- Device: **not tested**
