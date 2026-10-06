import json
import os
from typing import Any

SYSTEM_PROMPT = '''أنت وكيل محلي على هاتف Android داخل Termux. أجب بالعربية باختصار.
لا تنفذ أدوات بنفسك. عندما يطلب المستخدم تنفيذ أمر طرفية، أعد JSON فقط بهذا الشكل:
{"kind":"shell","command":"...","reason":"..."}
للمهام التي لا تحتاج طرفية أعد:
{"kind":"answer","text":"..."}
الأوامر يجب أن تعمل داخل مساحة العمل المسموحة فقط. لا تقترح sudo أو su أو أوامر حذف شامل أو قراءة الأسرار.
'''


def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"kind": "answer", "text": text}
    except json.JSONDecodeError:
        return {"kind": "answer", "text": text}


async def ask_model(user_text: str) -> dict[str, Any]:
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    prompt = SYSTEM_PROMPT + "\nطلب المستخدم:\n" + user_text
    if provider == "gemini":
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = await client.aio.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return _json_from_text(response.text or "{}")
    if provider in {"openai", "local"}:
        from openai import AsyncOpenAI
        if provider == "local":
            base_url = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:11434/v1")
            api_key = os.getenv("LOCAL_API_KEY", "local")
            model = os.getenv("LOCAL_MODEL", "llama3.2")
        else:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            api_key = os.environ["OPENAI_API_KEY"]
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}],
            response_format={"type": "json_object"},
        )
        return _json_from_text(response.choices[0].message.content or "{}")
    raise ValueError(f"مزود غير معروف: {provider}")
