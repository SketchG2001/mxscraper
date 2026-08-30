package com.mxscraper.app;

import android.util.Log;
import com.chaquo.python.Python;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Starts the existing FastAPI app via Chaquopy. No scraper logic here.
 */
final class LocalApiServer {
    private static final String TAG = "MxLocalApi";
    private static volatile boolean started;
    private static volatile boolean ready;

    private LocalApiServer() {}

    static synchronized void start(
            int port, String downloadDir, String ffmpegPath, String nativeLibDir) {
        if (started) {
            Log.i(TAG, "FastAPI already requested on 127.0.0.1:" + port);
            return;
        }
        started = true;
        new Thread(() -> pollHealth(port), "mx-fastapi-health").start();
        new Thread(
                () -> {
                    try {
                        Log.i(TAG, "Python runtime starting uvicorn on 127.0.0.1:" + port);
                        Python.getInstance()
                                .getModule("android_server")
                                .callAttr(
                                        "start",
                                        port,
                                        downloadDir,
                                        ffmpegPath,
                                        nativeLibDir);
                        Log.i(TAG, "uvicorn thread exited");
                    } catch (Exception e) {
                        started = false;
                        Log.e(TAG, "Python FastAPI failed to start", e);
                    }
                },
                "mx-fastapi")
                .start();
    }

    private static void pollHealth(int port) {
        HttpURLConnection conn = null;
        for (int i = 0; i < 120; i++) {
            try {
                URL url = new URL("http://127.0.0.1:" + port + "/health");
                conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(250);
                conn.setReadTimeout(250);
                conn.setUseCaches(false);
                int code = conn.getResponseCode();
                if (code == 200) {
                    ready = true;
                    Log.i(TAG, "FastAPI ready at http://127.0.0.1:" + port + "/health");
                    return;
                }
                if (i == 0 || i % 20 == 19) {
                    Log.w(TAG, "health HTTP " + code);
                }
            } catch (Exception e) {
                if (i == 0 || i % 20 == 19) {
                    Log.w(TAG, "health wait: " + e.getMessage());
                }
            } finally {
                if (conn != null) {
                    conn.disconnect();
                    conn = null;
                }
            }
            try {
                Thread.sleep(250);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
        Log.e(TAG, "FastAPI /health did not succeed on 127.0.0.1:" + port);
    }

    static boolean isReady() {
        return ready;
    }
}
