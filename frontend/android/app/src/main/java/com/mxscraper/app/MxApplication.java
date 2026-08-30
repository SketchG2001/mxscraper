package com.mxscraper.app;

import android.util.Log;
import com.chaquo.python.android.PyApplication;

/** Starts Chaquopy, then the loopback FastAPI process. */
public class MxApplication extends PyApplication {
    private static final String TAG = "MxLocalApi";

    @Override
    public void onCreate() {
        super.onCreate();
        java.io.File downloads = new java.io.File(getFilesDir(), "downloads");
        if (!downloads.exists() && !downloads.mkdirs()) {
            Log.e(TAG, "Could not create app-private downloads directory");
        }
        String ffmpeg = FfmpegLocator.ensure(this);
        Log.i(
                TAG,
                "Python runtime starting; FastAPI target 127.0.0.1:"
                        + BuildConfig.LOCAL_API_PORT
                        + " downloads="
                        + downloads.getAbsolutePath());
        LocalApiServer.start(
                BuildConfig.LOCAL_API_PORT,
                downloads.getAbsolutePath(),
                ffmpeg,
                getApplicationInfo().nativeLibraryDir);
    }
}
