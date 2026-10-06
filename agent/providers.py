import json
import os
from typing import Any
import httpx

SYSTEM_PROMPT = '''أنت وكيل محلي على هاتف Android داخل Termux. أجب بالعربية باختصار.
للسؤال العادي أعد JSON بهذا الشكل فقط:
{"kind":"answer","text":"..."}
لتنفيذ أمر واحد أعد:
{"kind":"shell","command":"...","reason":"..."}
لتنفيذ عدة خطوات مترابطة أعد:
{"kind":"batch","commands":["الأمر الأول","الأمر الثاني"],"reason":"..."}
لا تضع Markdown خارج JSON. لا تنفذ الأدوات بنفسك.
لِلمهام البرمجية استخدم مسارات واضحة. لا تضع الأسرار في الأوامر أو المخرجات.
مهم: يجب أن يكون ردك كائن JSON صالحًا، وأن تكون kind إحدى: answer أو shell أو batch.
'''

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "kind": {"type": "STRING", "enum": ["answer", "shell", "batch"]},
        "text": {"type": "STRING"},
        "command": {"type": "STRING"},
        "commands": {"type": "ARRAY", "items": {"type": "STRING"}},
        "reason": {"type": "STRING"},
    },
    "required": ["kind"],
}


def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"kind": "answer", "text": text}
    except json.JSONDecodeError:
        return {"kind": "answer", "text": text}


async def _gemini(user_text: str, context: str = "") -> dict[str, Any]:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": f"السياق المحفوظ:\n{context}\n\nالطلب الحالي:\n{user_text}"}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": RESPONSE_SCHEMA},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, params={"key": key}, json=body)
        response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _json_from_text(text)


async def ask_model(user_text: str, context: str = "") -> dict[str, Any]:
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return await _gemini(user_text, context)
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
