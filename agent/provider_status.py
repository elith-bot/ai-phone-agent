import os
import httpx

async def check_provider(name: str) -> dict:
    try:
        if name == "groq":
            key = os.environ.get("GROQ_API_KEY")
            if not key: return {"provider": name, "status": "no-key"}
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"})
            return {"provider": name, "status": "online" if response.is_success else f"http-{response.status_code}", "quota": "Groq API لا يعرض عدادًا موحدًا للحصة في هذا endpoint"}
        if name == "openrouter":
            key = os.environ.get("OPENROUTER_API_KEY")
            if not key: return {"provider": name, "status": "no-key"}
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"})
            data = response.json().get("data", {}) if response.is_success else {}
            return {"provider": name, "status": "online" if response.is_success else f"http-{response.status_code}", "limit": data.get("limit"), "usage": data.get("usage"), "rate_limit": data.get("rate_limit")}
        if name == "gemini":
            key = os.environ.get("GEMINI_API_KEY")
            if not key: return {"provider": name, "status": "no-key"}
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key})
            return {"provider": name, "status": "online" if response.is_success else f"http-{response.status_code}"}
        if name == "local":
            base = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(base + "/models")
            return {"provider": name, "status": "online" if response.is_success else f"http-{response.status_code}"}
    except Exception as exc:
        return {"provider": name, "status": "error", "detail": str(exc)[:160]}
    return {"provider": name, "status": "unknown"}

async def all_provider_status() -> list[dict]:
    return [await check_provider(name) for name in ("groq", "openrouter", "gemini", "local")]
