from __future__ import annotations

import json
import os
from typing import Any

import httpx


def _base() -> str:
    return os.getenv("ANDROID_ACCESS_URL", "http://127.0.0.1:8765").rstrip("/")


def _headers() -> dict[str, str]:
    token = os.getenv("ANDROID_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("ضع ANDROID_ACCESS_TOKEN في .env بعد نسخه من تطبيق AI Phone Companion")
    return {"Authorization": f"Bearer {token}"}


async def _call(method: str, endpoint: str, body: dict[str, Any] | None = None) -> str:
    timeout = float(os.getenv("ANDROID_ACCESS_TIMEOUT", "15"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, _base() + endpoint, headers=_headers(), json=body)
        response.raise_for_status()
        data = response.json()
    if data.get("ok") is False:
        raise RuntimeError(data.get("error", "فشل أمر Accessibility"))
    return json.dumps(data, ensure_ascii=False)


async def accessibility_health() -> str:
    return await _call("GET", "/health")


async def accessibility_snapshot() -> str:
    return await _call("GET", "/snapshot")


async def accessibility_click(query: str) -> str:
    return await _call("POST", "/click", {"query": query})


async def accessibility_type(text: str) -> str:
    return await _call("POST", "/type", {"text": text})


async def accessibility_back() -> str:
    return await _call("POST", "/back", {})


async def accessibility_home() -> str:
    return await _call("POST", "/home", {})
