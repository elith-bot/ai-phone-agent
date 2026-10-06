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
