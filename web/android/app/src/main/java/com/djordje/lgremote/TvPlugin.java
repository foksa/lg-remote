package com.djordje.lgremote;

import android.content.Context;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.util.Log;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PermissionState;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.MulticastSocket;
import java.net.NetworkInterface;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Talks to LG NetCast TVs (UDAP/2.0) directly from the phone, and finds them on the Wi-Fi. */
@CapacitorPlugin(
    name = "Tv",
    permissions = @Permission(alias = TvPlugin.LOCAL_NETWORK, strings = { "android.permission.ACCESS_LOCAL_NETWORK" })
)
public class TvPlugin extends Plugin {

    static final String LOCAL_NETWORK = "localNetwork";
    // Android 17 (API 37) put LAN access behind a runtime permission; older versions don't know it.
    private static final int API_LOCAL_NETWORK_PERMISSION = 37;
    private static final String TAG = "TvPlugin";
    private static final int TV_PORT = 8080;
    private static final Pattern MODEL = Pattern.compile("UDAP/[\\d.]+\\s+([^/\\s]+)");
    private final ExecutorService io = Executors.newCachedThreadPool();

    /** POST an UDAP envelope; resolves {status} where 0 means the TV couldn't be reached. */
    @PluginMethod
    public void send(PluginCall call) {
        if (needsPermission(call)) return;
        String ip = call.getString("ip");
        String path = call.getString("path");
        String body = call.getString("body", "");
        io.execute(() -> {
            JSObject ret = new JSObject();
            ret.put("status", post(ip, path, body));
            call.resolve(ret);
        });
    }

    /** Resolves {on} — the TV's network stack is down in standby, so any HTTP answer means it's on. */
    @PluginMethod
    public void isOn(PluginCall call) {
        if (needsPermission(call)) return;
        String ip = call.getString("ip");
        io.execute(() -> {
            JSObject ret = new JSObject();
            ret.put("on", probe(ip, 1500) != null);
            call.resolve(ret);
        });
    }

    /** GET an UDAP data target (e.g. cur_channel); resolves {status, body}. */
    @PluginMethod
    public void data(PluginCall call) {
        if (needsPermission(call)) return;
        String ip = call.getString("ip");
        String target = call.getString("target");
        io.execute(() -> call.resolve(get("http://" + ip + ":" + TV_PORT + "/udap/api/data?target=" + target, 4000)));
    }

    /** GET any URL on the home network (the guide on the Pi); resolves {status, body}. */
    @PluginMethod
    public void fetch(PluginCall call) {
        if (needsPermission(call)) return;
        String url = call.getString("url");
        io.execute(() -> call.resolve(get(url, 15000)));
    }

    /** Resolves {tvs: [{ip, model}]}: SSDP first, then a sweep of the local /24 if nothing answered. */
    @PluginMethod
    public void discover(PluginCall call) {
        if (needsPermission(call)) return;
        io.execute(() -> {
            Map<String, String> found = Collections.synchronizedMap(new LinkedHashMap<>());
            ssdp(found);
            if (found.isEmpty()) sweep(found);
            JSArray tvs = new JSArray();
            for (Map.Entry<String, String> e : found.entrySet()) {
                JSObject tv = new JSObject();
                tv.put("ip", e.getKey());
                tv.put("model", e.getValue());
                tvs.put(tv);
            }
            JSObject ret = new JSObject();
            ret.put("tvs", tvs);
            call.resolve(ret);
        });
    }

    /** Asks for the local network permission if needed; the call is replayed once the user answers. */
    private boolean needsPermission(PluginCall call) {
        if (Build.VERSION.SDK_INT < API_LOCAL_NETWORK_PERMISSION) return false;
        if (getPermissionState(LOCAL_NETWORK) == PermissionState.GRANTED) return false;
        requestPermissionForAlias(LOCAL_NETWORK, call, "onLocalNetworkPermission");
        return true;
    }

    @PermissionCallback
    private void onLocalNetworkPermission(PluginCall call) {
        if (getPermissionState(LOCAL_NETWORK) != PermissionState.GRANTED) {
            call.reject("Local network permission denied", "PERMISSION_DENIED");
            return;
        }
        switch (call.getMethodName()) {
            case "send": send(call); break;
            case "isOn": isOn(call); break;
            case "data": data(call); break;
            case "fetch": fetch(call); break;
            default: discover(call); break;
        }
    }

    private int post(String ip, String path, String body) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL("http://" + ip + ":" + TV_PORT + "/udap/api/" + path).openConnection();
            c.setConnectTimeout(3000);
            c.setReadTimeout(4000);
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("User-Agent", "UDAP/2.0");
            c.setRequestProperty("Content-Type", "text/xml; charset=utf-8");
            try (OutputStream out = c.getOutputStream()) {
                out.write(body.getBytes(StandardCharsets.UTF_8));
            }
            return c.getResponseCode();
        } catch (Exception e) {
            return 0;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private JSObject get(String url, int timeoutMs) {
        JSObject ret = new JSObject();
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(3000);
            c.setReadTimeout(timeoutMs);
            c.setRequestProperty("User-Agent", "UDAP/2.0");
            int status = c.getResponseCode();
            ret.put("status", status);
            if (status == 200) {
                // HttpURLConnection asks for gzip and unpacks it on its own.
                try (java.io.InputStream in = c.getInputStream()) {
                    java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
                    byte[] buf = new byte[16384];
                    for (int n; (n = in.read(buf)) > 0; ) out.write(buf, 0, n);
                    ret.put("body", out.toString("UTF-8"));
                }
            }
        } catch (Exception e) {
            ret.put("status", 0);
        } finally {
            if (c != null) c.disconnect();
        }
        return ret;
    }

    /** Returns the model name if an LG UDAP TV answers at ip, otherwise null. */
    private String probe(String ip, int timeoutMs) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL("http://" + ip + ":" + TV_PORT + "/").openConnection();
            c.setConnectTimeout(timeoutMs);
            c.setReadTimeout(timeoutMs);
            c.setRequestProperty("User-Agent", "UDAP/2.0");
            c.getResponseCode();
            return modelFrom(c.getHeaderField("Server"));
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static String modelFrom(String server) {
        if (server == null || !server.contains("UDAP")) return null;
        Matcher m = MODEL.matcher(server);
        return m.find() ? m.group(1) : "LG TV";
    }

    private void ssdp(Map<String, String> found) {
        WifiManager wifi = (WifiManager) getContext().getApplicationContext().getSystemService(Context.WIFI_SERVICE);
        WifiManager.MulticastLock lock = wifi.createMulticastLock("lg-remote-ssdp");
        lock.acquire();
        try (MulticastSocket sock = new MulticastSocket(null)) {
            sock.setReuseAddress(true);
            sock.bind(new InetSocketAddress(0));
            sock.setSoTimeout(500);
            InetAddress group = InetAddress.getByName("239.255.255.250");
            String msg = "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\nST: udap:rootservice\r\n\r\n";
            byte[] out = msg.getBytes(StandardCharsets.US_ASCII);
            for (int i = 0; i < 2; i++) sock.send(new DatagramPacket(out, out.length, group, 1900));

            long end = System.currentTimeMillis() + 3000;
            byte[] buf = new byte[2048];
            while (System.currentTimeMillis() < end) {
                DatagramPacket p = new DatagramPacket(buf, buf.length);
                try {
                    sock.receive(p);
                } catch (SocketTimeoutException e) {
                    continue;
                }
                String reply = new String(p.getData(), 0, p.getLength(), StandardCharsets.US_ASCII);
                for (String line : reply.split("\r\n")) {
                    if (line.toUpperCase().startsWith("SERVER:")) {
                        String model = modelFrom(line.substring(7).trim());
                        if (model != null) found.put(p.getAddress().getHostAddress(), model);
                    }
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "SSDP search failed, falling back to sweep", e);
        } finally {
            lock.release();
        }
    }

    private void sweep(Map<String, String> found) {
        String prefix = localPrefix();
        if (prefix == null) return;
        ExecutorService pool = Executors.newFixedThreadPool(48);
        for (int i = 1; i < 255; i++) {
            String ip = prefix + i;
            pool.execute(() -> {
                String model = probe(ip, 700);
                if (model != null) found.put(ip, model);
            });
        }
        pool.shutdown();
        try {
            pool.awaitTermination(10, TimeUnit.SECONDS);
        } catch (InterruptedException ignored) {
        }
    }

    /** "192.168.1." for the phone's Wi-Fi address, or null if not on an IPv4 network. */
    private static String localPrefix() {
        try {
            for (NetworkInterface nif : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!nif.isUp() || nif.isLoopback() || !nif.getName().startsWith("wlan")) continue;
                for (InetAddress a : Collections.list(nif.getInetAddresses())) {
                    if (a instanceof Inet4Address) {
                        String ip = a.getHostAddress();
                        return ip.substring(0, ip.lastIndexOf('.') + 1);
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return null;
    }
}
