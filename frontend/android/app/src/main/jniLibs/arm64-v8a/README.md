# Android FFmpeg (`libffmpeg.so`)

Do **not** copy `bin/ffmpeg` from this repository. Those files are Linux AArch64 ELF binaries, not Android Bionic.

Place only an **official-source LGPL** build here:

```text
libffmpeg.so
```

Build recipe: `docs/ffmpeg-android.md`.

Until this file exists, the app reports `FFmpeg unavailable` and rejects downloads.
