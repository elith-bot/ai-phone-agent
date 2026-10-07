import asyncio
import json
import os
from typing import Any
import httpx

SYSTEM_PROMPT = '''أنت وكيل محلي على هاتف Android داخل Termux. أجب بالعربية باختصار.
للسؤال العادي أعد JSON بهذا الشكل فقط:
{"kind":"answer","text":"..."}
لتنفيذ أمر واحد أعد:
{"kind":"shell","command":"...","reason":"..."}
لتَنفيذ عدة خطوات مترابطة أعد:
{"kind":"batch","commands":["الأمر الأول","الأمر الثاني"],"reason":"..."}
لعمليات الملفات المنظمة، فضّل أداة واحدة بهذا الشكل:
{"kind":"tool","tool":"filesystem.create|filesystem.read|filesystem.update|filesystem.search|filesystem.delete|terminal.run|config.ensure_paths|adb.devices|adb.ui_dump|adb.ui_find|adb.tap","arguments":{},"reason":"..."}
لا تضع Markdown خارج JSON. لا تنفذ الأدوات بنفسك.
لِلمهام البرمجية استخدم مسارات واضحة. لا تضع الأسرار في الأوامر أو المخرجات.
مهم: يجب أن يكون ردك كائن JSON صالحًا، وأن تكون kind إحدى: answer أو shell أو batch أو tool.
مجلد ملفات المستخدم الافتراضي هو PHONE_WORKSPACE_DIR، ويظهر في الهاتف باسم AI_Workspace. عند إنشاء HTML أو ملفات أو مجلدات للمستخدم استخدم هذا المجلد إذا لم يحدد مسارًا آخر.
جذر ذاكرة الهاتف هو PHONE_STORAGE_ROOT، ومجلد التنزيلات تحته باسم Download، ومجلد الصور باسم Pictures.
إذا طلب المستخدم مجلدًا بجانب Download فاستخدم PHONE_STORAGE_ROOT/اسم_المجلد. لا تستخدم مجلد Termux الداخلي لملفات المستخدم إلا إذا طلب ذلك صراحة.
'''

RESPONSE_SCHEMA = {"type": "OBJECT", "properties": {"kind": {"type": "STRING", "enum": ["answer", "shell", "batch", "tool"]}, "text": {"type": "STRING"}, "command": {"type": "STRING"}, "commands": {"type": "ARRAY", "items": {"type": "STRING"}}, "reason": {"type": "STRING"}, "tool": {"type": "STRING"}, "arguments": {"type": "OBJECT"}}, "required": ["kind"]}

def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"kind": "answer", "text": text}
    except json.JSONDecodeError:
        return {"kind": "answer", "text": text}

async def _gemini(user_text: str, context: str = "", model: str | None = None) -> dict[str, Any]:
    model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]}, "contents": [{"role": "user", "parts": [{"text": f"السياق المحفوظ:\n{context}\n\nالطلب الحالي:\n{user_text}"}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": RESPONSE_SCHEMA}}
    async with httpx.AsyncClient(timeout=60) as client:
        response = None
        for attempt in range(3):
            response = await client.post(url, params={"key": key}, json=body)
            if response.status_code != 429: break
            await asyncio.sleep(2 ** attempt)
        if response is not None and response.status_code == 429: raise RuntimeError("Gemini مشغول أو تجاوز حد الطلبات (429).")
        assert response is not None
        response.raise_for_status()
    return _json_from_text(response.json()["candidates"][0]["content"]["parts"][0]["text"])

async def _compatible_chat(base_url: str, api_key: str, model: str, user_text: str, context: str) -> dict[str, Any]:
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"السياق المحفوظ:\n{context}\n\nالطلب الحالي:\n{user_text}"}], "response_format": {"type": "json_object"}}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=body)
        response.raise_for_status()
    return _json_from_text(response.json()["choices"][0]["message"]["content"] or "{}")

async def ask_multimodal(content: list[dict[str, Any]], provider: str, model: str) -> str:
    if provider not in {"groq", "openrouter"}:
        raise RuntimeError("المعالجة متعددة الوسائط الحالية تستخدم Groq أو OpenRouter")
    base_url = "https://api.groq.com/openai/v1" if provider == "groq" else "https://openrouter.ai/api/v1"
    key = os.environ["GROQ_API_KEY" if provider == "groq" else "OPENROUTER_API_KEY"]
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": model, "messages": [{"role": "user", "content": content}]})
        response.raise_for_status()
    return response.json()["choices"][0]["message"].get("content", "")

async def ask_model(user_text: str, context: str = "", provider: str | None = None, model: str | None = None) -> dict[str, Any]:
    provider = (provider or os.getenv("AI_PROVIDER", "gemini")).lower()
    if provider == "gemini": return await _gemini(user_text, context, model)
    if provider == "local": return await _compatible_chat(os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:11434/v1"), os.getenv("LOCAL_API_KEY", "local"), model or os.getenv("LOCAL_MODEL", "llama3.2"), user_text, context)
    if provider == "openai": return await _compatible_chat(os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), os.environ["OPENAI_API_KEY"], model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"), user_text, context)
    if provider == "groq": return await _compatible_chat("https://api.groq.com/openai/v1", os.environ["GROQ_API_KEY"], model or os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"), user_text, context)
    if provider == "openrouter": return await _compatible_chat("https://openrouter.ai/api/v1", os.environ["OPENROUTER_API_KEY"], model or os.getenv("OPENROUTER_MODEL", "openrouter/free"), user_text, context)
    raise ValueError(f"مزود غير معروف: {provider}")
