package com.elithbot.aiphonecompanion;

import android.app.Activity;
import android.os.Bundle;
import android.provider.Settings;
import android.content.Intent;
import android.graphics.Color;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.security.SecureRandom;

public class MainActivity extends Activity {
    private static String token(android.content.Context context) {
        android.content.SharedPreferences p = context.getSharedPreferences("agent", MODE_PRIVATE);
        String value = p.getString("token", null);
        if (value == null) {
            byte[] bytes = new byte[18];
            new SecureRandom().nextBytes(bytes);
            StringBuilder b = new StringBuilder();
            for (byte x : bytes) b.append(String.format("%02x", x));
            value = b.toString();
            p.edit().putString("token", value).apply();
        }
        return value;
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(36, 36, 36, 36);
        TextView title = new TextView(this);
        title.setText("AI Phone Companion"); title.setTextSize(24); title.setTextColor(Color.rgb(20, 70, 120));
        TextView info = new TextView(this);
        info.setText("فعّل خدمة AI Phone Accessibility من إعدادات Android، ثم ضع الرمز في .env داخل Termux.");
        info.setTextSize(16); info.setPadding(0, 24, 0, 16);
        TextView token = new TextView(this);
        token.setText("رمز الاتصال المحلي:\n" + token(this)); token.setTextIsSelectable(true); token.setTextSize(15);
        Button settings = new Button(this); settings.setText("فتح إعدادات Accessibility");
        settings.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        Button refresh = new Button(this); refresh.setText("تحديث الحالة");
        refresh.setOnClickListener(v -> info.setText("فعّل الخدمة من القائمة، ثم أعد المحاولة من Telegram.\nالعنوان المحلي: 127.0.0.1:8765"));
        root.addView(title, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(info, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(token, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(settings, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(refresh, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(root);
    }
}
