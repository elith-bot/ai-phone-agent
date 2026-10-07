# الوسائط وفحص حالة المزودات

أضيفت معالجات Telegram التالية:

- الصور: `photo_message` ثم Groq Vision أو OpenRouter Vision.
- الصوت والبصمات: Groq Whisper لتحويل الصوت إلى نص ثم تمريره للعقل.
- PDF: تنزيل الملف واستخراج النص محليًا بواسطة `pypdf` ثم تمريره إلى موجه النماذج.
- الفيديو: تنزيله، استخراج لقطات عبر `ffmpeg`، وتحليل أول ثلاث لقطات بصريًا.
- البحث: الأمر `/web نص البحث` يستخدم DuckDuckGo ثم يمرر النتائج للعقل للتلخيص.

## أوامر الفحص

```text
/models
```

يعرض الكتالوج والعداد المحلي.

```text
/health
```

يفحص Groq وOpenRouter وGemini والنموذج المحلي عبر API. ملاحظة: بعض المزودات لا تعرض الحصة الكاملة من endpoint عام؛ لذلك نفرق بين `online` وعداد الاستخدام المحلي.

## اعتماديات الهاتف

بعد تحديث المشروع:

```bash
pkg install ffmpeg -y
cd ~/ai_phone_agent
git pull
source .venv/bin/activate
pip install -r requirements.txt
python -m agent.bot
```

ضع المفاتيح في `.env`:

```env
GROQ_API_KEY=
OPENROUTER_API_KEY=
GEMINI_API_KEY=
```

المعالجة قد تكون أبطأ فقط عندما يرسل المستخدم ملفًا كبيرًا أو فيديو؛ أما اختيار النموذج نفسه فمحلي وسريع ولا يضيف استدعاء نموذج إضافيًا.
