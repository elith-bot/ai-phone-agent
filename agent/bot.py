import asyncio
import logging
import os
import secrets
import shlex
import sys
from pathlib import Path
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from .providers import ask_model
from .tools import phone_workspace, run_shell, validate_command, workspace, is_delete_command
from .memory import add_memory, add_message, get_context, init_db, stats
from .tool_registry import execute_tool
from .model_router import ModelRouter
from .media import download_telegram_file, extract_pdf, groq_transcribe, video_frames, vision_answer, web_search
from .provider_status import all_provider_status

ROUTER = ModelRouter()

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
PENDING: dict[str, tuple[int, list[str]]] = {}
ACTIVE_TASKS: dict[str, dict[str, object]] = {}


def allowed(update: Update) -> bool:
    configured = os.getenv("TELEGRAM_ADMIN_USER_ID", "").strip()
    return bool(configured) and str(update.effective_user.id) == configured


async def deny(update: Update):
    await update.effective_message.reply_text("غير مصرح بهذا الحساب.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    await update.message.reply_text("أهلًا. أنفذ المهام العادية تلقائيًا، وأطلب موافقة بزر واحد قبل حذف الملفات. أرسل /status للمعلومات، /tasks للمهام الجارية، أو /restart لإعادة التشغيل.")


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram user ID: {update.effective_user.id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    messages, memories = stats(update.effective_user.id)
    active = "لا توجد" if not ACTIVE_TASKS else "، ".join(str(item["label"]) for item in ACTIVE_TASKS.values())
    await update.message.reply_text(f"المزود: {os.getenv('AI_PROVIDER','gemini')}\nالوضع: full-with-delete-approval\nمساحة التنفيذ: {workspace()}\nملفات المستخدم: {phone_workspace()}\nالمهام النشطة: {active}\nالذاكرة: {messages} رسالة، {memories} ذاكرة")


async def memory_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    messages, memories = stats(update.effective_user.id)
    await update.message.reply_text(f"الذاكرة محفوظة محليًا في SQLite.\nالرسائل: {messages}\nالذكريات: {memories}\nالسياق الحديث يُعاد تلقائيًا مع كل طلب.")


async def models_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    lines = []
    for row in ROUTER.status():
        limits = f"{row['used_today']}/{row['daily_limit'] or 'غير محدد'} يوميًا"
        lines.append(f"{row['key']} | {row['provider']} | {'متاح' if row['healthy'] else 'غير متاح'} | {limits}")
    await update.message.reply_text("كتالوج النماذج:\n" + "\n".join(lines))


async def health_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    rows = await all_provider_status()
    await update.message.reply_text("حالة المزودات عبر API:\n" + "\n".join(str(row) for row in rows))


async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    content = " ".join(context.args).strip()
    if not content:
        return await update.message.reply_text("استخدم: /remember اسمي ليث وأهتم ببرمجة ألعاب HTML")
    add_memory(update.effective_user.id, content)
    await update.message.reply_text("تم حفظها في الذاكرة الدائمة المحلية.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    removed = len(PENDING)
    PENDING.clear()
    await update.message.reply_text(f"تم إلغاء {removed} عملية حذف معلقة.")


async def tasks_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    if not ACTIVE_TASKS:
        return await update.message.reply_text("لا توجد مهام خلفية تعمل حاليًا.")
    lines = [f"{task_id}: {item['label']} — الخطوة {item['step']}/{item['total']}" for task_id, item in ACTIVE_TASKS.items()]
    await update.message.reply_text("المهام الخلفية النشطة:\n" + "\n".join(lines))


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    await update.message.reply_text("سأعيد تشغيل الوكيل الآن. انتظر ثوانٍ ثم أرسل /status.")
    await asyncio.sleep(0.8)
    os.execv(sys.executable, [sys.executable, "-m", "agent.bot"])


async def _task_heartbeat(update: Update, task_id: str):
    while True:
        await asyncio.sleep(int(os.getenv("TASK_HEARTBEAT_SECONDS", "20")))
        item = ACTIVE_TASKS.get(task_id)
        if item:
            await update.effective_message.reply_text(f"ما زلت أعمل: {item['label']} — الخطوة {item['step']}/{item['total']} قيد التنفيذ.")


async def execute_commands(update: Update, commands: list[str]):
    task_id = secrets.token_urlsafe(4)
    ACTIVE_TASKS[task_id] = {"label": "مهمة أوامر", "step": 0, "total": len(commands)}
    heartbeat = asyncio.create_task(_task_heartbeat(update, task_id))
    results = []
    try:
        for index, command in enumerate(commands, 1):
            ACTIVE_TASKS[task_id]["step"] = index
            code, output = await run_shell(command)
            results.append(f"الخطوة {index} ({code})\n$ {command}\n{output or 'تم التنفيذ بلا مخرجات'}")
            if code != 0:
                results.append("فشلت هذه الخطوة، لكن سأتابع بقية خطوات المهمة.")
        text = "\n\n".join(results)
        add_message(update.effective_user.id, "tool", text)
        await update.effective_message.reply_text(f"اكتملت المهمة:\n\n{text}"[-9000:])
    finally:
        heartbeat.cancel()
        ACTIVE_TASKS.pop(task_id, None)


async def approve_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not allowed(update):
        await query.answer("غير مصرح", show_alert=True)
        return
    await query.answer()
    action, request_id = query.data.split(":", 1)
    pending = PENDING.pop(request_id, None)
    if not pending:
        return await query.edit_message_text("انتهت صلاحية هذه الموافقة أو أُلغيت.")
    _, commands = pending
    if action == "reject":
        return await query.edit_message_text("تم رفض العملية.")
    await query.edit_message_text("تمت الموافقة. بدأ تنفيذ المهمة...")
    await execute_commands(update, commands)


async def process_text(update: Update, text: str):
    if not allowed(update):
        return await deny(update)
    add_message(update.effective_user.id, "user", text)
    if text.startswith(("تذكر أن", "احفظ أن", "لا تنس أن")):
        add_memory(update.effective_user.id, text.split(" ", 2)[-1])
    saved_context = get_context(update.effective_user.id)
    tried = set()
    last_error = None
    active_model = None
    plan = None
    for _ in range(6):
        try:
            active_model, request_info = ROUTER.choose(text, exclude=tried)
        except Exception as exc:
            last_error = exc
            break
        tried.add(active_model.key)
        ROUTER.mark_started(active_model)
        try:
            plan = await ask_model(text, saved_context, provider=active_model.provider, model=active_model.model_id)
            if len(tried) > 1:
                await update.message.reply_text(f"تم التحويل تلقائيًا إلى النموذج المتاح: {active_model.key}")
            break
        except Exception as exc:
            last_error = exc
            logging.warning("model %s failed: %s", active_model.key, exc)
            ROUTER.mark_failure(active_model, 90)
            plan = None
    else:
        plan = None
    if plan is None:
        return await update.message.reply_text(f"تعذر الاتصال بالنماذج حاليًا بعد تجربة {len(tried)} نموذجًا: {last_error}")
    kind = plan.get("kind")
    if kind == "answer" and ("JSON" in str(plan.get("text", "")) or "وكيل" in str(plan.get("text", ""))) and any(word in text for word in ("أنشئ", "اعمل", "سوي", "اكتب", "برمج", "نفذ")):
        plan = await ask_model("حوّل الطلب إلى خطة تنفيذ فعلية، ولا تشرح الصيغة: " + text, saved_context, provider=active_model.provider, model=active_model.model_id)
        kind = plan.get("kind")
    if kind == "answer":
        answer = str(plan.get("text", "لم أفهم الطلب."))[:4000]
        add_message(update.effective_user.id, "assistant", answer)
        return await update.message.reply_text(answer)
    if kind == "tool":
        tool_name = str(plan.get("tool", ""))
        arguments = plan.get("arguments") or {}
        if tool_name == "filesystem.delete":
            commands = [f"rm -rf -- {shlex.quote(str(arguments.get('path', '')))}"]
        elif tool_name == "terminal.run":
            commands = [str(arguments.get("command", "")).strip()]
        else:
            async def run_registered_tool():
                task_id = secrets.token_urlsafe(4)
                ACTIVE_TASKS[task_id] = {"label": f"الأداة {tool_name}", "step": 1, "total": 1}
                heartbeat = asyncio.create_task(_task_heartbeat(update, task_id))
                try:
                    result = await execute_tool(tool_name, arguments)
                    add_message(update.effective_user.id, "tool", result)
                    await update.effective_message.reply_text(result[-9000:])
                except Exception as exc:
                    await update.effective_message.reply_text(f"فشل تنفيذ الأداة: {exc}")
                finally:
                    heartbeat.cancel()
                    ACTIVE_TASKS.pop(task_id, None)
            asyncio.create_task(run_registered_tool())
            return await update.message.reply_text(f"بدأت أداة {tool_name} تلقائيًا.")
    elif kind == "shell":
        commands = [str(plan.get("command", "")).strip()]
    elif kind == "batch":
        commands = [str(item).strip() for item in plan.get("commands", []) if str(item).strip()]
    else:
        return await update.message.reply_text("لم أفهم نوع المهمة التي اقترحها النموذج.")
    add_message(update.effective_user.id, "assistant", str(plan)[:12000])
    if not commands or any(validate_command(command) for command in commands):
        return await update.message.reply_text("رفضت المهمة لأنها فارغة أو غير صالحة.")
    delete_needed = any(is_delete_command(command) for command in commands)
    if delete_needed:
        request_id = secrets.token_urlsafe(8)
        PENDING[request_id] = (update.effective_user.id, commands)
        preview = "\n".join(f"{i}. `{command}`" for i, command in enumerate(commands, 1))
        keyboard = [[
            InlineKeyboardButton("موافقة على الحذف", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton("إلغاء", callback_data=f"reject:{request_id}"),
        ]]
        return await update.message.reply_text(
            f"هذه المهمة تتضمن حذفًا:\n{preview}\n\nهل توافق؟",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    # المهام العادية تبدأ فورًا؛ يمكن استقبال مهام أخرى بالتوازي.
    asyncio.create_task(execute_commands(update, commands))
    await update.message.reply_text(f"بدأت تنفيذ {len(commands)} خطوة تلقائيًا داخل {workspace()}. سأرسل النتيجة عند الانتهاء.")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    await process_text(update, update.message.text.strip())


async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await deny(update)
    try:
        path = await download_telegram_file(update.message, context, ".ogg")
        text = await groq_transcribe(path)
        await update.message.reply_text(f"النص المستخرج:\n{text}")
        await process_text(update, text)
    except Exception as exc:
        await update.message.reply_text(f"تعذر معالجة الصوت: {exc}")


async def photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await deny(update)
    try:
        path = await download_telegram_file(update.message, context, ".jpg")
        prompt = update.message.caption or "حلل الصورة واشرح ما فيها بالعربية."
        model, _ = ROUTER.choose(prompt, media="image")
        result = await vision_answer(path, prompt, model.provider, model.model_id)
        await update.message.reply_text(result[:9000])
    except Exception as exc:
        await update.message.reply_text(f"تعذر تحليل الصورة: {exc}")


async def document_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await deny(update)
    name = (update.message.document.file_name or "file").lower()
    try:
        path = await download_telegram_file(update.message, context, Path(name).suffix or ".bin")
        if name.endswith(".pdf"):
            text = extract_pdf(path)
            await process_text(update, f"حلل ملف PDF التالي وأجب عن طلب المستخدم السابق أو لخصه:\n{text}")
        else:
            await update.message.reply_text(f"تم تنزيل الملف محليًا: {path}. اطلب مني قراءته أو معالجته.")
    except Exception as exc:
        await update.message.reply_text(f"تعذر معالجة الملف: {exc}")


async def video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await deny(update)
    try:
        path = await download_telegram_file(update.message, context, ".mp4")
        frames = video_frames(path)
        if frames:
            prompt = update.message.caption or "حلل هذه اللقطة من الفيديو باختصار بالعربية."
            model, _ = ROUTER.choose(prompt, media="image")
            analyses = await asyncio.gather(*(vision_answer(frame, prompt, model.provider, model.model_id) for frame in frames[:3]), return_exceptions=True)
            text = "\n\n".join(f"اللقطة {i + 1}: {value}" for i, value in enumerate(analyses) if isinstance(value, str))
            await update.message.reply_text(f"استخرجت {len(frames)} لقطات من الفيديو:\n{text}"[:9000])
        else:
            await update.message.reply_text("استلمت الفيديو لكن لم أستطع استخراج لقطات. تأكد من تثبيت ffmpeg في Termux.")
    except Exception as exc:
        await update.message.reply_text(f"تعذر معالجة الفيديو: {exc}. تأكد من تثبيت ffmpeg في Termux.")


async def web_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return await deny(update)
    query = " ".join(context.args).strip()
    if not query: return await update.message.reply_text("استخدم: /web ابحث عن أحدث أخبار Android")
    try:
        results = await web_search(query)
        await process_text(update, f"لخص نتائج البحث التالية وأجب بالعربية مع ذكر الروابط:\n{results}")
    except Exception as exc:
        await update.message.reply_text(f"تعذر البحث: {exc}")


async def async_main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("ضع TELEGRAM_BOT_TOKEN في ملف .env")
    init_db()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", user_id))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("tasks", tasks_status))
    app.add_handler(CommandHandler("memory", memory_status))
    app.add_handler(CommandHandler("models", models_status))
    app.add_handler(CommandHandler("health", health_status))
    app.add_handler(CommandHandler("web", web_message))
    app.add_handler(CommandHandler("remember", remember))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CallbackQueryHandler(approve_delete, pattern=r"^(approve|reject):"))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_message))
    app.add_handler(MessageHandler(filters.PHOTO, photo_message))
    app.add_handler(MessageHandler(filters.Document.ALL, document_message))
    app.add_handler(MessageHandler(filters.VIDEO, video_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
