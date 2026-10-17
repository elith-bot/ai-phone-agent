# بحث وكلاء الذكاء الاصطناعي المفتوحة المصدر ومعمارية الوكيل المشترك

**تاريخ البحث:** 2026-10-11  
**النطاق:** وكلاء البرمجة والطرفية، وكلاء استخدام الكمبيوتر، وكلاء Android/ADB، ومشاريع حساب `elith-bot`.

## النتيجة المباشرة

نستطيع بناء وكيل واحد يعمل على الهاتف والكمبيوتر، لكن الأفضل ألا ندمج مشاريع كاملة داخل مشروعنا. التصميم الصحيح هو **نواة وكيل واحدة مستقلة عن الجهاز**، ثم طبقات تنفيذ منفصلة:

```text
Telegram / CLI / واجهة محلية
          ↓
النواة: التخطيط، الذاكرة، الأحداث، السياسات، التحقق
          ↓
سجل الأدوات الموحد
          ↓
Termux | Android/ADB | Linux | Windows | Browser
```

معظم المشاريع القوية التي جرى فحصها لا تدعم Termux أو Android-host رسميًا. بعضها يستطيع التحكم بهاتف Android من كمبيوتر خارجي عبر ADB، وبعضها يعمل على Linux/Windows لكنه ليس وكيل هاتف. لذلك سنقتبس **الأفكار والأنماط المعمارية**، ونكتب تكاملنا الخاص، بدل جمع وكلاء متنافسين داخل عملية واحدة.

## ما وجدناه في حساب `elith-bot`

| المشروع | ما يقدمه | القرار المقترح |
|---|---|---|
| [ai-phone-agent](https://github.com/elith-bot/ai-phone-agent) | النواة الحالية: Telegram، الذاكرة، توجيه النماذج، الوسائط، الأدوات، التنفيذ، وبداية ADB | الأساس الذي نطوره |
| [odysseus](https://github.com/elith-bot/odysseus) | مساحة عمل محلية فيها Chat وAgent وMCP وShell وWeb وSkills وMemory وبحث عميق وملفات | نقتبس فصل مساحة العمل، الذاكرة، المهارات، الجلسات، والبحث؛ لا ندمجه كاملًا في الهاتف الآن |
| [agent-swarm](https://github.com/elith-bot/agent-swarm) | نموذج قائد/عمال، عزل للعمال، تقدم حي، SQLite، قنوات متعددة، وتعلم من نتائج الجلسات | نقتبس مدير المهام، العمال، سجل التقدم، والعزل؛ Docker غير مناسب كشرط للهاتف |
| بقية المستودعات | مشاريع مواقع وألعاب وتطبيقات | ليست مصادر مباشرة لنواة الوكيل |

README مشروع `odysseus` يذكر صراحةً أدوات shell وMCP والويب والملفات والمهارات والذاكرة، إضافة إلى ضغط السياق والبحث متعدد الخطوات. أما `agent-swarm` فيفصل Lead عن Workers ويرسل التقدم إلى لوحة أو قنوات خارجية. هذان المشروعان مفيدان كمرجعين معماريين، لكن لا ننسخ تطبيقاتهما كاملة إلى `ai-phone-agent`.

## أهم المشاريع الخارجية

### 0. OpenClaw-Termux

اكتُشف بعد إعداد هذا التقرير، لذلك لم يكن ضمن قائمة المشاريع المفحوصة سابقًا. يضيف OpenClaw Gateway داخل Ubuntu عبر proot-distro، وتطبيق Flutter بواجهة Setup وTerminal وDashboard وLogs وForeground Service، إضافة إلى Node capabilities للهاتف. يدعم Telegram رسميًا من خلال Gateway، لكنه لا يستبدل Accessibility العامة تلقائيًا. نستخدمه كطبقة تشغيل وواجهة، ونبقي ذاكرة SQLite وCRUD وpatch وTermux:API وADB وAccessibility الخاصة بمشروعنا خلف Skills أو Adapter محلي. [22]

**ما نقتبسه:** دورة حياة Gateway، الواجهة الرسومية، Dashboard، foreground service، Node protocol، onboarding، وإدارة القنوات.

### 1. OpenHands

OpenHands ممتاز كمرجع لفصل `Agent` عن `Conversation` و`Workspace`، وسجل أحداث typed من نوع Action/Observation، وضغط السياق، واستئناف الجلسة، وسجل الأدوات، وملاحظات الأمان. يدعم Local Workspace وRemote Workspace وDocker Workspace وAgent Server، لكنه لا يقدم دعمًا رسميًا لـTermux أو ADB أو التحكم بشاشة Android. تشغيله محليًا دون عزل يعطي الوكيل وصولًا واسعًا للنظام، لذلك نقتبس مبادئه ولا نجعله اعتمادًا للهاتف. [1] [2]

**ما نقتبسه:** `Agent Loop`، الأحداث append-only، `Tool Registry` typed، condenser، callbacks، resume، وواجهة Workspace قابلة للتبديل.

### 2. Goose

Goose وكيل عام محلي مبني حول runtime وامتدادات MCP وSQLite للجلسات والذاكرة وسياقات المشروع والمستخدم. يملك Manual Approval وSmart Approval وChat Only، وRecipes، وSubagents، وAuto-compaction، وMax Turns. دعمه الرسمي يركز على macOS/Linux/Windows، ويوجد مستودع منفصل `goose-mobile` يحتوي PoC Android تجريبيًا لا يصلح أساسًا إنتاجيًا. [3] [4]

**ما نقتبسه:** الامتدادات المعلنة، `available_tools`، الذاكرة ذات النطاقين، Recipes، subagents، إدارة السياق، وسياسات الموافقة.

### 3. Cline وRoo Code

Cline مهم بسبب فصل Plan/Act، والموافقات لكل فئة أداة، وMCP، وMemory Bank، وCheckpoints، وCLI/SDK. Cline نشط، لكن ثنائيات CLI الرسمية توثق Linux وWindows وmacOS، لا Android/Termux. Roo Code مؤرشف ومتوقف، لذلك نستخدمه مرجعًا تاريخيًا فقط ولا نعتمد عليه. [5] [6]

**ما نقتبسه:** وضع `Plan` للقراءة والتحليل، وضع `Act` للتنفيذ، الموافقات حسب الأداة، Git checkpoints، وملفات ذاكرة المشروع القابلة للمراجعة.

### 4. Open Interpreter

الإصدار الحالي يقدم runtime طرفية محليًا، جلسات resume/fork/compact، skills، MCP، subagents، وطبقات sandbox/approval منفصلة. لكنه لا يثبت دعم Android أو Termux أو ADB، وأوضاع مثل `danger-full-access` و`--yolo` خطرة على جهاز حقيقي. [7]

**ما نقتبسه:** الفصل بين runtime وharness وmodel adapter، واجهة JSONL، الجلسات، الإلغاء، ووضوح مستويات الصلاحية.

### 5. Aider وSWE-agent

Aider قوي في البرمجة الطرفية: Repo Map، وضع Architect ثم Editor، Git diff/undo، lint/test، والإصلاح بعد فشل الاختبارات. لكنه ليس وكيل جهاز ولا يملك ADB رسميًا، وتثبيته في Termux يواجه اعتماديات native. [8]

SWE-agent يقدم فصل Agent عن Environment/Deployment، أدوات ACI، تقليص التاريخ، trajectories قابلة لإعادة التشغيل، وstate JSON. لكنه يعتمد على Docker غالبًا، وهو في وضع maintenance-only، ولا يقدم تحكم GUI أو هاتف. [9]

**ما نقتبسه:** خريطة المشروع، دورة edit→test→repair، state بعد كل فعل، replay، وتقليص السياق.

### 6. Agent S وOSWorld وBrowserGym

Agent S يقدم حلقة observe→reason/reflect→one action→verify للتحكم البصري بالكمبيوتر، مع grounding وReflection. OSWorld وBrowserGym يقدمان واجهات منظمة من نوع `reset/step/observation/action/validate` وتسجيل trajectory، لكنهما بيئات بحث/تقييم ثقيلة وليسا طبقة إنتاج للهاتف. لا يوجد دعم ADB موثق في هذه المشاريع. [10] [11]

**ما نقتبسه:** واجهة observation/action/verification، reflection، evaluator مستقل، وadapters منفصلة للمتصفح وسطح المكتب.

### 7. MobileUse وAppAgent وAndroidWorld

MobileUse وAppAgent هما الأقرب إلى طبقة هاتف Android. كلاهما يجمع screenshot مع UI tree/Accessibility أو UIAutomator، ثم يخطط لفعل محدد مثل click/type/swipe، وينفذه عبر ADB، ثم يلتقط حالة جديدة. MobileUse يضيف Planner وOperator وReflector وProgressor وNoteTaker وحدودًا للخطوات وإعادة المحاولة. AppAgent يضيف استكشاف التطبيقات وتوثيق عناصر الواجهة في ملفات. AndroidWorld أقرب إلى benchmark ومحاكي قابل للتكرار من كونه وكيلًا جاهزًا. [12] [13] [14]

**ما نقتبسه:** فصل `AndroidBackend` عن النموذج، نموذج أفعال JSON محدود، screenshot + UI tree، reflection بعد الفعل، app knowledge، max steps/retries، وassertions بعد التنفيذ.

### 8. Callstack agent-device

هذا من أقوى المراجع العملية لطبقة Android: daemon محلي، CLI وMCP وNode API على عقد واحد، capabilities، sessions، device leases، snapshots، refs مؤقتة، selectors ثابتة، artifacts، logs، replay وverification. يدعم Android عبر ADB، لكنه لا يثبت تشغيله داخل Termux نفسه. يتطلب Node.js حديثًا وADB. [15]

**ما نقتبسه:** `capabilities` قبل الفعل، `open→snapshot→act→verify→close`، قفل الجهاز لمنع وكيلين من التحكم معًا، وملفات replay.

## القرار المعماري المقترح

### الطبقة 1: الواجهة

- Telegram للمحادثة والتنبيهات والموافقة والإلغاء.
- CLI/Termux للتشغيل المحلي والتشخيص.
- واجهة HTTP محلية اختيارية لاحقًا.
- إخراج JSONL للأحداث حتى يمكن ربط الوكيل بواجهة أو محرر كود.

### الطبقة 2: Capability Broker

يسجل قدرات الجهاز الحالي بدل افتراضها:

```text
filesystem
shell
network
screenshot
accessibility
adb
install
input
browser
```

إذا لم تكن capability موجودة، لا يسمح الوكيل للنموذج باختيار الأداة ولا يعطي نجاحًا زائفًا.

### الطبقة 3: Policy وSecurity Gate

كل أداة تعلن:

- read-only أو write أو destructive.
- هل هي قابلة لإعادة التنفيذ بأمان؟
- المسارات المسموحة.
- هل تحتاج شبكة؟
- هل تحتاج موافقة؟
- هل يمكن إلغاؤها؟

الصلاحية الكاملة لا تكون افتراضية. نستخدم `safe`، ثم موافقة خاصة قبل الحذف، التثبيت، تغيير الإعدادات، الرسائل، الدفع، أو shell غير المسموح.

### الطبقة 4: Orchestrator وAgent Loop

الدورة الموحدة:

```text
request
  → plan
  → tool call
  → policy check
  → execute
  → observation
  → verification
  → memory/state update
  → next step أو finish
```

يجب أن تكون كل خطوة قابلة للإلغاء والتسجيل وإعادة التشغيل.

### الطبقة 5: Tool Registry

نوسع سجلنا الحالي إلى أدوات منظمة:

```text
filesystem.read
filesystem.search
filesystem.create
filesystem.update
filesystem.delete
terminal.run
web.search
browser.open
android.devices
android.capabilities
android.screenshot
android.read_ui
android.open_app
android.click
android.long_press
android.swipe
android.type
android.key
android.back
android.home
android.wait
android.logcat
```

لا نعطي النموذج `adb shell` خامًا كخيار افتراضي. يحوّل الوكيل الطلب إلى فعل typed، ويطلب موافقة عندما يكون الفعل حساسًا.

### الطبقة 6: Platform Adapters

- `TermuxAdapter`: shell وTermux:API والملفات المحلية.
- `AndroidAdbAdapter`: ADB إلى هاتف أو محاكي محدد بالـserial.
- `LinuxAdapter`: subprocess وAT-SPI عند الحاجة.
- `WindowsAdapter`: PowerShell/Win32 أو WSL كخيار.
- `BrowserAdapter`: Playwright مقيد.
- `scrcpy`: خيار رؤية وإدخال من مضيف Linux/Windows، وليس اعتمادًا إلزاميًا داخل الهاتف.

## خطة ADB التي لم تكتمل بعد

1. تثبيت Platform-Tools من مصدر موثوق.
2. تفعيل USB debugging وقبول RSA.
3. تنفيذ `adb devices -l` وتخزين serial، لا اسم بشري فقط.
4. إضافة `android.capabilities` لفحص الإصدار والدقة والحزمة الحالية وscreenshot وUIAutomator وIME وclipboard وinstall وlogcat.
5. إضافة `android.screenshot` و`android.read_ui`.
6. إضافة أفعال: open app، click، long press، swipe، scroll، type، key، back، home، wait.
7. بعد كل فعل: screenshot + UI tree + current package + stdout/stderr.
8. تحقق مستقل: ظهور عنصر، تغير النص، تغير الحزمة، أو تحقق assertion.
9. إعادة المحاولة فقط للأفعال idempotent؛ لا نعيد install/delete/شراء تلقائيًا.
10. إضافة device lease حتى لا يتحكم وكيلان بالجهاز في الوقت نفسه.
11. دعم Unicode عبر IME اختياري مثل ADBKeyBoard بعد موافقة المستخدم.
12. اختبار USB ثم wireless pairing على Android 11+، مع عدم تعريض ADB port للشبكة العامة.
13. اختبار هاتف حقيقي ومحاكي، Android 11–15، Linux وWindows، وتطبيقات ذات UI مختلفة.

**ملاحظة حاسمة:** التحكم بهاتف Android من كمبيوتر عبر ADB مثبت ومدعوم في عدد من المشاريع. أما تشغيل الوكيل وADB بالكامل داخل الهاتف نفسه عبر Termux فليس مثبتًا رسميًا في هذه المشاريع، ويجب اعتباره مسارًا تجريبيًا حتى نختبره فعليًا.

## ما لا ندمجه

- لا ندمج OpenHands أو Goose أو Cline كاملًا داخل `ai-phone-agent`.
- لا نجعل Docker شرطًا للهاتف.
- لا نعتمد Roo Code لأنه مؤرشف ومتوقف.
- لا نعتمد SWE-agent كقاعدة رئيسية لأنه maintenance-only وDocker-oriented.
- لا نستخدم OSWorld/BrowserGym كطبقة إنتاج؛ نستخدم أفكارهما كاختبارات وواجهات.
- لا نشغل MobileUse وAppAgent معًا كوكيلين متنافسين؛ نقتبس منهما ونكتب `AndroidAdbAdapter` واحدًا.
- لا نفعّل YOLO أو danger-full-access في جهاز شخصي.
- لا ننسخ كودًا من GPL/Apache/MIT دون SBOM وإشعارات وتدقيق تبعيات.

## مراحل التنفيذ

1. **نواة حتمية:** event schema، tool registry، policy gate، checkpoints، replay، masking، وإلغاء.
2. **وكيل برمجي محدود:** read/search/edit/test/git مع Plan/Act وdiff وrepair.
3. **Termux minimal:** shell وملفات وTermux:API بلا تبعيات native ثقيلة.
4. **ADB MVP:** discovery، serial، screenshot، UI tree، click/type/swipe/back/home/open/wait.
5. **اعتمادية الهاتف:** leases، capabilities، retries، reconnect، Unicode، logcat، تنقية artifacts.
6. **Linux/Windows:** browser وAT-SPI أو screen adapter خلف نفس observe/act/verify.
7. **الذاكرة والموديلات:** task memory، project memory، model router، local/cloud fallback، وقياس الجودة.
8. **التقييم:** replay suite، AndroidWorld، prompt-injection tests، مراجعة تراخيص وSBOM، pin للإصدارات، وخطة rollback.

## استراتيجية النماذج

- Planner نصي أرخص للتخطيط وتقسيم المهمة.
- Operator بصري عند الحاجة إلى screenshot/Android UI.
- Verifier مستقل يتحقق من الأثر ولا يكتفي بـexit code.
- نموذج محلي صغير على الهاتف للطلبات النصية البسيطة والحساسة.
- نموذج محلي متوسط على Linux/Windows عبر Ollama أو LM Studio أو vLLM عند توفر الموارد.
- نموذج سحابي أقوى فقط للتخطيط الصعب أو الرؤية المعقدة، بعد تنقية البيانات وموافقة سياسة الخصوصية.

نقيس النجاح بعد التحقق، ونسبة الأفعال الخطرة، والزمن، والذاكرة، وليس جودة الإجابة النصية فقط.

## المخاطر الرئيسية

- قيود Android 12+ قد تقتل العمليات الخلفية.
- Android-host وTermux قد يفشلان بسبب native wheels أو ADB أو Node.
- Prompt injection من صفحة أو تطبيق قد يحاول تغيير الخطة.
- نجاح أمر shell لا يعني نجاح الأثر المطلوب.
- UI وresource IDs تتغير بين التطبيقات والإصدارات.
- ADB اللاسلكي يزيد سطح المخاطر.
- النماذج السحابية قد ترسل صورًا أو أسرارًا إلى مزود خارجي.
- اختلاف تراخيص MIT وApache-2.0 وGPLv3 والنماذج والتبعيات.

## الخلاصة التنفيذية

سنحوّل `ai-phone-agent` إلى **نواة Agent/Conversation/Event Loop مع سجل أدوات typed وطبقة capabilities وADB adapter قابل للتبديل**. نأخذ أفضل الأفكار من OpenHands وGoose وCline وOpen Interpreter وAider، ونأخذ طبقة الهاتف من MobileUse وAppAgent وagent-device، ونستخدم AndroidWorld وOSWorld كمرجع اختبار. لا ننسخ وكلاء كاملين ولا نجعل أي مشروع خارجي شرطًا لتشغيل الهاتف.

الخطوة التالية المنطقية قبل كتابة الكود هي تصميم عقود الأدوات والـevents و`AndroidAdbAdapter`، ثم اختبار ADB على جهاز/محاكي. لا نبدأ بدمج مئات المشاريع؛ نبدأ بنواة صغيرة قابلة للتدقيق ثم نضيف القدرات واحدة واحدة.

## المراجع

[1]: https://docs.openhands.dev/sdk/arch/agent "OpenHands Agent architecture"
[2]: https://docs.openhands.dev/sdk/arch/tool-system "OpenHands tool system"
[3]: https://goose-docs.ai/docs/guides/context-engineering/ "Goose context engineering"
[4]: https://github.com/aaif-goose/goose-mobile "Goose Mobile experimental Android agent"
[5]: https://docs.cline.bot/core-workflows/plan-and-act "Cline Plan and Act"
[6]: https://roocodeinc.github.io/Roo-Code/ "Roo Code documentation and project status"
[7]: https://www.openinterpreter.com/docs/terminal/sandbox "Open Interpreter sandbox and permissions"
[8]: https://aider.chat/docs/repomap.html "Aider repository map"
[9]: https://swe-agent.com/latest/background/architecture/ "SWE-agent architecture"
[10]: https://github.com/simular-ai/Agent-S "Agent S repository"
[11]: https://github.com/xlang-ai/OSWorld "OSWorld repository"
[12]: https://github.com/MadeAgents/mobile-use "MobileUse repository"
[13]: https://github.com/tencentqqgylab/appagent "AppAgent repository"
[14]: https://github.com/google-research/android_world "AndroidWorld repository"
[15]: https://oss.callstack.com/agent-device/docs/quick-start "Callstack agent-device quick start"
[16]: https://github.com/elith-bot/ai-phone-agent "مشروع ai-phone-agent الحالي"
[17]: https://github.com/elith-bot/odysseus "مشروع Odysseus في حساب elith-bot"
[18]: https://github.com/elith-bot/agent-swarm "مشروع Agent Swarm في حساب elith-bot"
[19]: https://developer.android.com/tools/adb "Android Debug Bridge official documentation"
[20]: https://github.com/Genymobile/scrcpy "scrcpy repository"
[21]: https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent "Termux RUN_COMMAND Intent"
[22]: https://github.com/mithun50/openclaw-termux "OpenClaw-Termux repository"
