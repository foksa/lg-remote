package com.djordje.lgremote;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(TvPlugin.class);
        super.onCreate(savedInstanceState);
        // The remote is laid out to fit the screen; the WebView's own scrollbar only flashes on swipes.
        getBridge().getWebView().setVerticalScrollBarEnabled(false);
        getBridge().getWebView().setHorizontalScrollBarEnabled(false);
    }
}
