package com.mxscraper.app;

import android.os.Bundle;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

/**
 * One native back path: ask the SPA, then background the task only on Home.
 * Capacitor App plugin back handling is disabled (capacitor.config.ts) to avoid
 * duplicate events (notifyListeners + document backbutton).
 */
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getOnBackPressedDispatcher()
                .addCallback(
                        this,
                        new OnBackPressedCallback(true) {
                            @Override
                            public void handleOnBackPressed() {
                                WebView webView =
                                        getBridge() != null ? getBridge().getWebView() : null;
                                if (webView == null) {
                                    moveTaskToBack(true);
                                    return;
                                }
                                webView.evaluateJavascript(
                                        "(function(){try{"
                                                + "if(typeof window.__mxConsumeBack==='function'){"
                                                + "return window.__mxConsumeBack();}"
                                                + "if(document.getElementById('header-search-panel')){"
                                                + "return 'search';}"
                                                + "if(document.fullscreenElement){"
                                                + "document.exitFullscreen();return 'fs';}"
                                                + "if(location.pathname!=='/'){history.back();return 'hist';}"
                                                + "return 'min';"
                                                + "}catch(e){return 'min';}})()",
                                        result -> {
                                            String r =
                                                    result == null
                                                            ? ""
                                                            : result.replace("\"", "");
                                            if ("min".equals(r) || "none".equals(r) || r.isEmpty()) {
                                                MainActivity.this.moveTaskToBack(true);
                                            }
                                        });
                            }
                        });
    }
}
