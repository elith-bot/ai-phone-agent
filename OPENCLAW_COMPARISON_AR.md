# مقارنة OpenClaw-Termux مع ai-phone-agent وخطة الدمج

**التاريخ:** 2026-10-17

## النتيجة

OpenClaw-Termux لم يكن موجودًا في تقرير الوكلاء السابق المحفوظ في `RESEARCH_AGENTS_AR.md`. لذلك لا نعدّه واحدًا من المشاريع التي فُحصت سابقًا. هو اكتشاف جديد يجب إضافته إلى المقارنة.

القرار المقترح هو استخدام OpenClaw-Termux كطبقة التشغيل والواجهة الأساسية على Android، مع عدم حذف `ai-phone-agent`. نُبقي مشروعنا كطبقة مخصصة للذاكرة العربية، اختيار النماذج، الموافقات، أدوات الملفات، Termux:API، Accessibility، وتجميع الرسائل. لا نُشغّل بوت Telegram القديم والجديد في الوقت نفسه باستخدام نفس Token، لأن ذلك يسبب تعارضًا في polling واستلام الرسائل.

## ماذا يقدم OpenClaw-Termux؟

المشروع يثبت OpenClaw Gateway داخل Ubuntu يعمل عبر `proot-distro`، ويوفر تطبيق Flutter مستقلًا مع واجهة إعداد، Terminal مدمج، Dashboard، سجلات، إعداد النماذج، وتشغيل Gateway في الخلفية. كما يوفر نسخة CLI باسم `openclawx` تعمل من Termux. يذكر README أنه يدعم Android 10 أو أحدث، ويحتاج تقريبًا إلى 500MB لتنزيل Ubuntu وNode.js وOpenClaw، ولا يحتاج Root. [1]

واجهة Flutter هي أكبر إضافة مقارنة بمشروعنا الحالي. فهي تحتوي على Setup Wizard، مؤشرات حالة Gateway، Web Dashboard، شاشة سجلات، إعدادات، خدمة foreground، وإدارة Node للهاتف. [1]

طبقة Node في OpenClaw تعرض قدرات Android مثل الكاميرا، الفلاش، الموقع، تسجيل الشاشة، الحساسات، الاهتزاز، والاتصال التسلسلي. لكنها ليست Accessibility Service عامة للتحكم في كل تطبيقات الهاتف. بعض القدرات تتطلب بقاء الشاشة مفتوحة أو إحضار التطبيق إلى الواجهة. [1]

## المقارنة العملية

| المجال | OpenClaw-Termux | ai-phone-agent الحالي | القرار |
|---|---|---|---|
| واجهة الهاتف | Flutter UI وDashboard وTerminal وLogs | Telegram وCLI؛ Companion بسيط قيد البناء | نعتمد واجهة OpenClaw ونربط قدراتنا خلفها |
| تشغيل Android | Gateway داخل Ubuntu عبر proot أو CLI Termux | Python مباشرة داخل Termux | OpenClaw مناسب كـ runtime، وPython تبقى طبقة خدمات |
| Telegram | دعم رسمي عبر Gateway، مع pairing وallowlists وأزرار وموافقات | Bot مخصص مع batching ومهام خلفية وذاكرة | نستخدم قناة واحدة فقط؛ الأفضل أن يملكها OpenClaw بعد الاختبار |
| النماذج | مزودون متعددون من خلال OpenClaw | Groq وOpenRouter وGemini وlocal مع router وحالة الحصة | نحتفظ بـ model router أو نحوّله إلى Provider/Skill داخل OpenClaw |
| الذاكرة | جلسات وذاكرة OpenClaw بحسب إعداداته | SQLite وذاكرة هوية وسياق عربية مخصصة | لا نستبدل SQLite قبل اختبار parity؛ نضيف جسرًا تدريجيًا |
| الملفات والكود | أدوات OpenClaw/skills وTerminal | CRUD وpatch ذري وdiff ومسارات هاتف | نحتفظ بأدوات patch وpolicy لأنها من أقوى أجزاء مشروعنا |
| التحكم بالواجهة | Node commands وليست Accessibility عامة | ADB + Accessibility Companion محلي | نضيف طبقة Accessibility كأداة/Plugin، ولا نفترض أن OpenClaw يغطيها |
| الخلفية | Foreground service وbattery guidance | مهام طويلة وheartbeat وإلغاء من Telegram | نربط مراقبة المهام، مع تجنب تشغيل نظامين متوازيين |
| الأمان | Pairing وallowlist وtool policies، مع تحذير من صلاحية التخزين الكامل | safe mode، موافقة الحذف، مسارات محمية، event log | نوحّد السياسة ونبقي الموافقات الحساسة إلزامية |
| التثبيت | APK اختياري أو CLI؛ التطبيق ينزل بيئة كبيرة | Termux وPython فقط | نبدأ CLI، ثم APK الواجهة بعد نجاح الاختبار |

## هل يحتاج Google Play أو APK؟

لا يحتاج المسار الأول إلى APK أو Google Play. يمكن استخدام Termux من F-Droid ثم تثبيت CLI وتشغيل `openclawx setup`. هذا هو المسار الأقل تغييرًا والأقل مساحة، لكنه يتطلب تنزيل Ubuntu وNode.js وOpenClaw داخل proot. [1]

APK الخاص بـ `openclaw-termux` اختياري إذا أردنا واجهته الرسومية، وTerminal المدمج، Dashboard، إدارة Gateway، foreground service، وNode capabilities. لا يلزم Google Play؛ يمكن تنزيل APK من GitHub Releases أو بناؤه من المصدر. لكن يجب اختيار قناة تثبيت واحدة لأن APK من Google Play وAPK sideload قد يستخدمان توقيعًا مختلفًا، وقد يتطلب الانتقال بينهما إزالة النسخة القديمة وفقدان بياناتها المحلية. [2]

لا نمنح صلاحية التخزين الكامل تلقائيًا. توثيق المشروع نفسه يحذر من `MANAGE_EXTERNAL_STORAGE` لأنه يسمح بقراءة وتعديل كل الصور والتنزيلات والملفات. نستخدم مجلد `AI_Workspace` فقط، ونطلب الصلاحية الأوسع فقط إذا احتجناها وبعد موافقة واضحة. [1]

## Telegram والنماذج

OpenClaw يدعم Telegram رسميًا عبر Gateway، ويستخدم pairing افتراضيًا للمحادثات الخاصة، مع allowlists للمستخدمين والمجموعات، وأزرار inline، وموافقات لتنفيذ الأوامر. [3]

لكن لا يجوز تشغيل بوتنا الحالي وOpenClaw مع نفس Token في الوقت نفسه. في Telegram يجب أن يكون polling أو webhook مملوكًا لعملية واحدة. لذلك سيكون الاختبار الأول بأحد الخيارين:

1. **المسار المفضل:** نوقف `ai-phone-agent`، نضع Token البوت نفسه في إعداد OpenClaw، ونقيد `allowFrom` بمعرّف المستخدم `695866288` بعد تدوير Token المكشوف سابقًا.
2. **مسار الجسر:** يبقى Python هو مالك Telegram ويستدعي OpenClaw Gateway عبر واجهته المحلية. هذا يحافظ على كودنا الحالي، لكنه يحتاج Adapter موثقًا ومختبرًا للبروتوكول، وقد يكرر بعض وظائف Telegram.

بما أن المطلوب هو جعل OpenClaw أساسيًا مع واجهته، فالمسار الأول أنظف. نضيف وظائفنا الخاصة كـ skills/plugins أو خدمة محلية محدودة، بدل إبقاء بوتين متنافسين.

## ما الذي نحتفظ به من مشروعنا؟

لا ننسخ OpenClaw أو نستبدل كل شيء. نحتفظ بالطبقات التي تعالج احتياجات المستخدم مباشرة:

- الذاكرة العربية وهوية المستخدم في SQLite.
- تجميع الرسائل السريعة في طلب واحد.
- خطة متعددة الخطوات مع heartbeat وإلغاء وإعادة محاولة محدودة.
- `filesystem.patch` الذري مع diff والتحقق من فرادة المقطع.
- مسارات `AI_Workspace` ومنع الخروج من الجذور المسموحة.
- سياسة الموافقة قبل الحذف والتثبيت وتغيير الإعدادات والعمليات الحساسة.
- Termux:API.
- ADB وAccessibility Companion للهاتف نفسه.
- Model catalog وfallback، مع قياس الحالة والحصة عندما يسمح المزود بذلك.

نقتبس من OpenClaw الواجهة، gateway lifecycle، dashboard، foreground service، node protocol، وسهولة الإعداد؛ ولا ندمج مستودعًا كاملًا داخل Python.

## خطة التنفيذ الآمنة

### المرحلة الأولى: تجربة منفصلة

ننشئ نسخة احتياطية من مشروعنا وبيئته، ثم نثبت CLI في Termux دون حذف مجلد `ai_phone_agent`. نتحقق من `openclawx status` و`doctor`، ثم نكمل onboarding بمفتاح جديد وليس بالمفاتيح التي ظهرت في سجل المحادثة.

### المرحلة الثانية: Telegram منفصل أو Token جديد

نستخدم Bot Token جديدًا للاختبار، ونقيد الوصول إلى معرف المستخدم فقط. لا نغيّر البوت الحالي حتى نتأكد من الذاكرة، الوسائط، الموافقات، وتنفيذ المهام. بعد النجاح نقرر هل ننقل البوت الأصلي بعد تدوير Token، أم نستخدم الجسر المحلي.

### المرحلة الثالثة: نقل وظائفنا

نحوّل الذاكرة وCRUD وpatch وTermux:API وAccessibility إلى Skills/Plugin أو خدمة محلية يستدعيها OpenClaw. كل أداة تعلن مستوى الخطر وتحتاج موافقة عندما تكون destructive أو تغيّر إعدادات الجهاز.

### المرحلة الرابعة: APK والواجهة

بعد نجاح CLI، نبني أو نثبت APK OpenClaw-Termux. لا نحتاج Google Play. نستخدم APK فقط لواجهة الإدارة وGateway وNode، وليس كبديل عن Termux:API أو Accessibility Companion إلا إذا أثبتت الاختبارات أن قدراته تغطي المطلوب.

## الحكم النهائي

OpenClaw أقوى من مشروعنا في الواجهة، إدارة Gateway، تشغيل الخلفية، Dashboard، وتجهيز Android. مشروعنا أقوى في التخصيص العربي، SQLite، workflow الحالي، patch الآمن، policy، اختيار النماذج، وتجميع الرسائل.

أفضل بنية ليست استبدالًا كاملًا، بل:

```text
OpenClaw Flutter UI / Gateway
            ↓
Telegram channel واحدة + جلسات OpenClaw
            ↓
Skills / local adapter الخاصة بنا
            ↓
SQLite + model router + patch + Termux:API + ADB + Accessibility
```

لن نثبّت APK أو نعدّل Token أو نوقف الوكيل الحالي تلقائيًا. الخطوة التالية العملية هي تجربة CLI في Termux بمسار منفصل وToken اختبار جديد، ثم توصيل Telegram بعد فحص الحالة.

## المصادر

[1]: https://github.com/mithun50/openclaw-termux "OpenClaw-Termux README and architecture"
[2]: https://docs.openclaw.ai/platforms/android "OpenClaw Android installation and APK guidance"
[3]: https://docs.openclaw.ai/channels/telegram "OpenClaw Telegram channel configuration and access control"
