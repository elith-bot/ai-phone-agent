import asyncio
import logging
import os
import secrets
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from .providers import ask_model
from .tools import run_shell, validate_command, workspace

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
PENDING: dict[int, tuple[str, str]] = {}


def allowed(update: Update) -> bool:
    configured = os.getenv("TELEGRAM_ADMIN_USER_ID", "").strip()
    return bool(configured) and str(update.effective_user.id) == configured


async def deny(update: Update):
    await update.effective_message.reply_text("غير مصرح. شغّل /id أولًا لمعرفة رقم حسابك ثم ضعه في .env وأعد التشغيل.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    await update.message.reply_text("أهلًا. أنا وكيلك المحلي داخل Termux. أرسل طلبًا أو استخدم /status و /cancel.")


async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Telegram user ID: {update.effective_user.id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    await update.message.reply_text(f"المزود: {os.getenv('AI_PROVIDER','gemini')}\nالوضع: {os.getenv('AGENT_MODE','safe')}\nالمساحة: {workspace()}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    PENDING.pop(update.effective_user.id, None)
    await update.message.reply_text("تم إلغاء العملية المعلقة.")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return await deny(update)
    uid = update.effective_user.id
    text = update.message.text.strip()
    if text.startswith("/confirm "):
        token = text.split(maxsplit=1)[1]
        pending = PENDING.pop(uid, None)
        if not pending or not secrets.compare_digest(token, pending[0]):
            return await update.message.reply_text("رمز التأكيد غير صالح أو منتهي.")
        code, output = await run_shell(pending[1])
        return await update.message.reply_text(f"النتيجة ({code}):\n{output or 'تم التنفيذ بلا مخرجات'}")
    try:
        plan = await ask_model(text)
    except Exception as exc:
        logging.exception("model failure")
        return await update.message.reply_text(f"تعذر الاتصال بالنموذج: {exc}")
    if plan.get("kind") != "shell":
        return await update.message.reply_text(str(plan.get("text", "لم أفهم الطلب."))[:4000])
    command = str(plan.get("command", "")).strip()
    reason = str(plan.get("reason", ""))
    if validate_command(command):
        return await update.message.reply_text("رفضت الأمر: أمر خطر أو غير صالح. استخدمه يدويًا بعد مراجعته.")
    token = secrets.token_urlsafe(6)
    PENDING[uid] = (token, command)
    await update.message.reply_text(f"سيُنفذ داخل {workspace()}:\n`{command}`\nالسبب: {reason}\n\nللتأكيد أرسل: /confirm {token}\nأو /cancel", parse_mode="Markdown")


async def async_main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("ضع TELEGRAM_BOT_TOKEN في ملف .env")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", user_id))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    app.add_handler(MessageHandler(filters.Regex(r"^/confirm "), message))
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
