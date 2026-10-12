# AI Phone Companion

هذا تطبيق Android صغير يضيف طبقة تحكم بواجهة الهاتف عبر `AccessibilityService`. يتواصل الوكيل الموجود في Termux معه على العنوان المحلي `127.0.0.1:8765` فقط.

## البناء والتثبيت

افتح مجلد `android_companion` في Android Studio، ثم نفّذ **Build APK(s)**. ثبّت `app-debug.apk` على الهاتف. يمكن أيضًا بناء المشروع من جهاز يحتوي Android SDK وGradle:

```bash
gradle --no-daemon assembleDebug
```

بعد التثبيت:

1. افتح **AI Phone Companion**.
2. انسخ رمز الاتصال الظاهر.
3. افتح إعدادات **Accessibility**.
4. فعّل **AI Phone Accessibility** ووافق على الإذن.
5. في Termux، أضف الرمز إلى ملف `.env`:

```env
ANDROID_ACCESS_URL=http://127.0.0.1:8765
ANDROID_ACCESS_TOKEN=ضع_الرمز_هنا
ANDROID_ACCESS_TIMEOUT=15
```

ثم أعد تشغيل الوكيل.

## الاختبار من Termux

```bash
curl -sS -H "Authorization: Bearer $ANDROID_ACCESS_TOKEN" "$ANDROID_ACCESS_URL/health"
curl -sS -H "Authorization: Bearer $ANDROID_ACCESS_TOKEN" "$ANDROID_ACCESS_URL/snapshot"
```

يجب أن يعيد الاختبار الأول JSON يحتوي على `"ok":true`. إذا ظهر `unauthorized` فتأكد من الرمز. إذا ظهر `connection refused` فتأكد أن خدمة Accessibility مفعلة وأن التطبيق يعمل.

## الأدوات المتاحة للوكيل

- `android.accessibility_health`: فحص الخدمة.
- `android.accessibility_snapshot`: قراءة عناصر النافذة الحالية.
- `android.accessibility_click`: الضغط على عنصر حسب النص أو الوصف أو معرف العرض.
- `android.accessibility_type`: الكتابة في حقل قابل للتحرير.
- `android.accessibility_back`: زر الرجوع.
- `android.accessibility_home`: زر الرئيسية.

هذه الطبقة لا تمنح صلاحية Root، ولا تتجاوز أذونات Android. لا تستخدم النقر أو الكتابة في عمليات حذف أو شراء أو تغيير إعدادات حساسة إلا بعد تأكيد المستخدم.
