# وكيل الهاتف المحلي — Termux + Telegram + Gemini

هذه **نسخة أولى آمنة** تعمل داخل Termux، وتستخدم Gemini افتراضيًا مع قابلية التبديل إلى OpenAI أو نموذج محلي متوافق مع OpenAI.

## المتطلبات

- هاتف Android.
- Termux من مصدر موثوق مثل F-Droid أو GitHub الرسمي.
- حساب Telegram وبوت من BotFather.
- مفتاح Gemini من Google AI Studio.
- لا تحتاج Root لهذه النسخة.

## التثبيت داخل Termux

```bash
pkg update -y && pkg install -y python git
termux-setup-storage
mkdir -p ~/ai_phone_agent
# انقل ملفات المشروع إلى هذا المجلد، ثم:
cd ~/ai_phone_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

ضع `TELEGRAM_BOT_TOKEN` و`GEMINI_API_KEY`. اترك `TELEGRAM_ADMIN_USER_ID` فارغًا أول مرة، ثم شغّل البوت وأرسل `/id`، ضع الرقم في `.env` وأعد التشغيل.

```bash
chmod 600 .env
mkdir -p ~/agent-workspace
source .venv/bin/activate
python -m agent.bot
```

## تبديل النموذج

في `.env`:

```env
AI_PROVIDER=gemini
# أو openai أو local
```

لـ OpenAI أضف `OPENAI_API_KEY`. وللنموذج المحلي شغّل خادمًا مثل Ollama واجعل `LOCAL_BASE_URL` و`LOCAL_MODEL` مناسبين.

## ربط Acode

اجعل `WORKSPACE_DIR` مجلدًا مشتركًا، مثل:

```env
WORKSPACE_DIR=/data/data/com.termux/files/home/storage/shared/Projects/agent-workspace
```

بعد `termux-setup-storage` سيظهر المجلد في الذاكرة الداخلية، ويمكن فتحه في Acode. لا تضع ملف `.env` داخل المجلد المشترك.

## الأمان

- البوت لا يقبل إلا رقم Telegram الموجود في `TELEGRAM_ADMIN_USER_ID`.
- كل أمر طرفية يطلب `/confirm TOKEN`.
- الأوامر الخطرة محجوبة مبدئيًا.
- التنفيذ محصور في `WORKSPACE_DIR` من ناحية مجلد العمل.
- لا ترسل توكن Telegram أو مفاتيح API في المحادثة أو إلى البوت.
- لا تفعّل Root الآن.

> ملاحظة: هذه نقطة بداية وليست تحكمًا كاملًا بواجهة Android. إضافة Tasker وTermux:API وAccessibility ستكون مرحلة لاحقة منفصلة وبصلاحيات واضحة.
