# تشغيل الوكيل بالخلفية في Termux

## تشغيل وإيقاف يدوي

من داخل مجلد المشروع:

```bash
chmod +x scripts/*.sh
./scripts/start_agent.sh
```

مشاهدة السجل:

```bash
tail -f logs/agent.log
```

إيقاف الوكيل:

```bash
./scripts/stop_agent.sh
```

## التشغيل بعد إعادة تشغيل الهاتف

1. ثبّت تطبيق **Termux:Boot** من نفس المصدر الذي ثبّت منه Termux.
2. افتح Termux:Boot مرة واحدة.
3. نفّذ داخل Termux:

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-agent <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 15
cd $HOME/ai_phone_agent
./scripts/start_agent.sh
EOF
chmod +x ~/.termux/boot/start-agent
```

بعد ذلك سيبدأ الوكيل بعد إقلاع الهاتف. أرسل `/status` في Telegram للتحقق.

## إعادة التشغيل من Telegram

بعد تحديث الكود أو إعدادات `.env`، أرسل للبوت:

```text
/restart
```

سيستبدل الوكيل عمليته الحالية ويبدأ من جديد. لا حاجة لإرسال `Ctrl+C` أو تشغيل `python -m agent.bot` يدويًا.

إذا لم يعد البوت بعد ثوانٍ، شغّله من Termux:

```bash
cd ~/ai_phone_agent
./scripts/start_agent.sh
```

## تحديث المشروع والبيئة بأمر واحد

بعد رفع تحديث جديد إلى GitHub، نفّذ:

```bash
cd ~/ai_phone_agent
./scripts/update_agent.sh
```

الأمر يقوم بالآتي:

1. إيقاف النسخة القديمة بأمان.
2. تنفيذ `git pull --ff-only` من المستودع.
3. إبقاء قيم `.env` الحالية، بما فيها مفاتيح API، دون طباعتها أو استبدالها.
4. إضافة الإعدادات الجديدة الناقصة فقط.
5. فحص صياغة Python وتثبيت الاعتماديات.
6. تشغيل الوكيل في الخلفية.

بعده أرسل `/status` و`/models` في Telegram. إذا كان `.env` غير موجود، ينشئ الأمر قالبًا جديدًا؛ عندها يجب ملء المفاتيح يدويًا قبل التشغيل.

## مهم في إعدادات Android

- عطّل تحسين البطارية لتطبيق Termux وTermux:Boot.
- اسمح لـTermux بالعمل في الخلفية والبيانات غير المقيّدة.
- لا تغلق Termux بالقوة من إعدادات التطبيقات.
- إذا كان الهاتف يغلق العمليات بقوة، فعّل التشغيل التلقائي لتطبيق Termux إن كان الخيار موجودًا.

## ملاحظات

- `termux-wake-lock` يقلل احتمال نوم العملية، لكنه قد يستهلك البطارية.
- `nohup` يجعل العملية تستمر بعد إغلاق جلسة الطرفية.
- هذا لا يجعل البوت يعمل إذا توقف الهاتف أو انقطع الإنترنت.
- لا تستخدم `termux-wake-lock` إذا أردت توفير البطارية؛ أوقف الوكيل أولًا عبر `./scripts/stop_agent.sh`.
