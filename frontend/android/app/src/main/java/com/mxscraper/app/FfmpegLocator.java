package com.mxscraper.app;

import android.content.Context;
import android.util.Log;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.channels.FileChannel;

/**
 * Copies a bundled Android FFmpeg (libffmpeg.so) into app-private storage.
 * Does not use the repo Linux bin/ffmpeg binaries.
 */
final class FfmpegLocator {
    private static final String TAG = "MxFfmpeg";

    private FfmpegLocator() {}

    static String ensure(Context context) {
        File nativeSo = new File(context.getApplicationInfo().nativeLibraryDir, "libffmpeg.so");
        if (!nativeSo.isFile()) {
            Log.w(TAG, "FFmpeg unavailable (no arm64 libffmpeg.so bundled)");
            return "";
        }
        File destDir = new File(context.getFilesDir(), "bin");
        if (!destDir.exists() && !destDir.mkdirs()) {
            Log.e(TAG, "FFmpeg unavailable (could not create bin dir)");
            return "";
        }
        File dest = new File(destDir, "ffmpeg");
        try {
            if (!dest.isFile() || dest.length() != nativeSo.length()) {
                copyFile(nativeSo, dest);
            }
            if (!dest.setExecutable(true, true)) {
                Log.w(TAG, "Could not mark FFmpeg executable");
            }
        } catch (IOException e) {
            Log.e(TAG, "FFmpeg copy failed", e);
            return "";
        }
        if (!runsVersion(dest)) {
            Log.e(TAG, "FFmpeg unavailable (ffmpeg -version failed)");
            return "";
        }
        Log.i(TAG, "FFmpeg available");
        return dest.getAbsolutePath();
    }

    private static boolean runsVersion(File ffmpeg) {
        Process process = null;
        try {
            process = new ProcessBuilder(ffmpeg.getAbsolutePath(), "-version").start();
            return process.waitFor() == 0;
        } catch (Exception e) {
            Log.e(TAG, "FFmpeg execution failed", e);
            return false;
        } finally {
            if (process != null) {
                process.destroy();
            }
        }
    }

    private static void copyFile(File src, File dest) throws IOException {
        try (FileChannel in = new FileInputStream(src).getChannel();
                FileChannel out = new FileOutputStream(dest).getChannel()) {
            in.transferTo(0, in.size(), out);
        }
    }
}
