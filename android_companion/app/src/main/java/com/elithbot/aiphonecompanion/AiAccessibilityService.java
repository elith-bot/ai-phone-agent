package com.elithbot.aiphonecompanion;

import android.accessibilityservice.AccessibilityService;
import android.os.Bundle;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.graphics.Rect;
import android.content.SharedPreferences;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

public class AiAccessibilityService extends AccessibilityService {
    private volatile boolean running;
    private ServerSocket server;
    private ExecutorService pool;

    @Override public void onServiceConnected() {
        super.onServiceConnected();
        running = true; pool = Executors.newCachedThreadPool();
        pool.execute(() -> {
            try { server = new ServerSocket(8765, 20, InetAddress.getByName("127.0.0.1"));
                while (running) pool.execute(() -> handleClient(serverAccept()));
            } catch (Exception ignored) { }
        });
    }
    private Socket serverAccept() { try { return server.accept(); } catch (Exception e) { return null; } }
    @Override public void onAccessibilityEvent(AccessibilityEvent event) { }
    @Override public void onInterrupt() { }
    @Override public void onDestroy() { running = false; try { if (server != null) server.close(); } catch (Exception ignored) {} if (pool != null) pool.shutdownNow(); super.onDestroy(); }

    private void handleClient(Socket socket) {
        if (socket == null) return;
        try (Socket s = socket) {
            s.setSoTimeout(5000);
            BufferedReader reader = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8));
            String request = reader.readLine(); if (request == null) return;
            String[] parts = request.split(" "); String method = parts[0]; String path = parts.length > 1 ? parts[1] : "/";
            int length = 0; String auth = ""; String line;
            while (!(line = reader.readLine()).isEmpty()) {
                String lower = line.toLowerCase();
                if (lower.startsWith("content-length:")) length = Integer.parseInt(line.substring(15).trim());
                if (lower.startsWith("authorization:")) auth = line.substring(14).trim();
            }
            char[] chars = new char[Math.min(length, 20000)]; int read = length > 0 ? reader.read(chars) : 0;
            String body = read > 0 ? new String(chars, 0, read) : "";
            String token = auth.startsWith("Bearer ") ? auth.substring(7).trim() : auth;
            String expected = getSharedPreferences("agent", MODE_PRIVATE).getString("token", "");
            String response;
            if (!expected.equals(token)) response = json("error", "unauthorized");
            else response = route(method, path, body);
            byte[] bytes = response.getBytes(StandardCharsets.UTF_8);
            OutputStream out = s.getOutputStream();
            out.write(("HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: " + bytes.length + "\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
            out.write(bytes); out.flush();
        } catch (Exception ignored) { }
    }
    private String route(String method, String path, String body) {
        if ("GET".equals(method) && "/health".equals(path)) return "{\"ok\":true,\"service\":\"accessibility\"}";
        if ("GET".equals(method) && "/snapshot".equals(path)) return snapshot();
        if ("POST".equals(method) && "/click".equals(path)) return click(jsonValue(body, "query"));
        if ("POST".equals(method) && "/type".equals(path)) return type(jsonValue(body, "text"));
        if ("POST".equals(method) && "/back".equals(path)) { performGlobalAction(GLOBAL_ACTION_BACK); return "{\"ok\":true}"; }
        if ("POST".equals(method) && "/home".equals(path)) { performGlobalAction(GLOBAL_ACTION_HOME); return "{\"ok\":true}"; }
        return json("error", "unknown_endpoint");
    }
    private String snapshot() { AccessibilityNodeInfo root = getRootInActiveWindow(); if (root == null) return "{\"ok\":false,\"error\":\"no_window\"}"; StringBuilder b = new StringBuilder("{\"ok\":true,\"nodes\":["); walk(root, b, new int[]{0}); if (b.charAt(b.length()-1) == ',') b.deleteCharAt(b.length()-1); b.append("]}"); root.recycle(); return b.toString(); }
    private void walk(AccessibilityNodeInfo n, StringBuilder b, int[] count) { if (count[0]++ > 200) return; Rect r = new Rect(); n.getBoundsInScreen(r); b.append("{\"text\":\"").append(esc(String.valueOf(n.getText()))).append("\",\"desc\":\"").append(esc(String.valueOf(n.getContentDescription()))).append("\",\"id\":\"").append(esc(String.valueOf(n.getViewIdResourceName()))).append("\",\"clickable\":").append(n.isClickable()).append(",\"bounds\":\"").append(r.toShortString()).append("\"},"); for (int i=0;i<n.getChildCount();i++) { AccessibilityNodeInfo c=n.getChild(i); if(c!=null) { walk(c,b,count); c.recycle(); } } }
    private String click(String query) { AccessibilityNodeInfo root=getRootInActiveWindow(); if(root==null)return json("error","no_window"); AccessibilityNodeInfo n=find(root,query); boolean ok=n!=null && n.performAction(AccessibilityNodeInfo.ACTION_CLICK); if(n!=null)n.recycle(); root.recycle(); return ok?"{\"ok\":true}":json("error","element_not_found"); }
    private AccessibilityNodeInfo find(AccessibilityNodeInfo n,String q) { String a=String.valueOf(n.getText())+" "+String.valueOf(n.getContentDescription())+" "+String.valueOf(n.getViewIdResourceName()); if(a.toLowerCase().contains(q.toLowerCase()))return AccessibilityNodeInfo.obtain(n); for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null){AccessibilityNodeInfo f=find(c,q);c.recycle();if(f!=null)return f;}}return null; }
    private String type(String text) { AccessibilityNodeInfo n=getRootInActiveWindow(); if(n==null)return json("error","no_window"); AccessibilityNodeInfo edit=findEditable(n); if(edit==null){n.recycle();return json("error","editable_not_found");} Bundle b=new Bundle();b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,text);boolean ok=edit.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b);edit.recycle();n.recycle();return ok?"{\"ok\":true}":json("error","type_failed"); }
    private AccessibilityNodeInfo findEditable(AccessibilityNodeInfo n){if(n.isEditable())return AccessibilityNodeInfo.obtain(n);for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);if(c!=null){AccessibilityNodeInfo f=findEditable(c);c.recycle();if(f!=null)return f;}}return null;}
    private String jsonValue(String body,String key){String marker="\""+key+"\"";int p=body.indexOf(marker);if(p<0)return"";p=body.indexOf(':',p);p=body.indexOf('"',p);int e=body.indexOf('"',p+1);return p>=0&&e>p?body.substring(p+1,e):"";}
    private String json(String k,String v){return "{\"ok\":false,\""+k+"\":\""+esc(v)+"\"}";}
    private String esc(String s){return s.replace("\\","\\\\").replace("\"","\\\"").replace("\n"," ").replace("\r"," ");}
}
