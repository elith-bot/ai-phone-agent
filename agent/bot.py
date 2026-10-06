import asyncio
import logging
import os
import secrets
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from .providers import ask_model
from .tools import run_shell, validate_command, workspace, is_delete_command
from .memory import add_memory, add_message, get_context, init_db, stats

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
PENDING: dict[str, tuple[int, list[str]]] = {}


def allowed(update: Update) -> bool:
    configured = os.getenv("TELEGRAM_ADMIN_USER_ID", "").strip()
    return bool(configured) and str(update.effective_user.id) == configured


async def deny(update: Update):
    await update.effective_message.reply_text("غير مصرح بهذا الحساب.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    await update.message.reply_text("أهلًا. أنفذ المهام العادية تلقائيًا، وأطلب موافقة بزر واحد قبل حذف الملفات. أرسل /status للمعلومات.")


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram user ID: {update.effective_user.id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    messages, memories = stats(update.effective_user.id)
    await update.message.reply_text(f"المزود: {os.getenv('AI_PROVIDER','gemini')}\nالوضع: full-with-delete-approval\nالمساحة: {workspace()}\nالذاكرة: {messages} رسالة، {memories} ذاكرة")


async def memory_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    messages, memories = stats(update.effective_user.id)
    await update.message.reply_text(f"الذاكرة محفوظة محليًا في SQLite.\nالرسائل: {messages}\nالذكريات: {memories}\nالسياق الحديث يُعاد تلقائيًا مع كل طلب.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    removed = len(PENDING)
    PENDING.clear()
    await update.message.reply_text(f"تم إلغاء {removed} عملية حذف معلقة.")


async def execute_commands(update: Update, commands: list[str]):
    results = []
    for index, command in enumerate(commands, 1):
        code, output = await run_shell(command)
        results.append(f"الخطوة {index} ({code})\n$ {command}\n{output or 'تم التنفيذ بلا مخرجات'}")
        if code != 0:
            results.append("توقفت المهمة لأن هذه الخطوة فشلت.")
            break
    text = "\n\n".join(results)
    add_message(update.effective_user.id, "tool", text)
    await update.effective_message.reply_text(f"اكتملت المهمة:\n\n{text}"[-9000:])


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


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    text = update.message.text.strip()
    add_message(update.effective_user.id, "user", text)
    saved_context = get_context(update.effective_user.id)
    try:
        plan = await ask_model(text, saved_context)
    except Exception as exc:
        logging.exception("model failure")
        return await update.message.reply_text(f"تعذر الاتصال بالنموذج: {exc}")
    kind = plan.get("kind")
    if kind == "answer" and ("JSON" in str(plan.get("text", "")) or "وكيل" in str(plan.get("text", ""))) and any(word in text for word in ("أنشئ", "اعمل", "سوي", "اكتب", "برمج", "نفذ")):
        plan = await ask_model("حوّل الطلب إلى خطة تنفيذ فعلية، ولا تشرح الصيغة: " + text, saved_context)
        kind = plan.get("kind")
    if kind == "answer":
        answer = str(plan.get("text", "لم أفهم الطلب."))[:4000]
        add_message(update.effective_user.id, "assistant", answer)
        return await update.message.reply_text(answer)
    if kind == "shell":
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


async def async_main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("ضع TELEGRAM_BOT_TOKEN في ملف .env")
    init_db()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", user_id))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("memory", memory_status))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(approve_delete, pattern=r"^(approve|reject):"))
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
