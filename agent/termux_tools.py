from __future__ import annotations

import asyncio
import json
import os
from typing import Any


async def _run(name: str, *args: str) -> str:
    timeout = max(5.0, float(os.getenv("TERMUX_API_TIMEOUT", "20")))
    proc = await asyncio.create_subprocess_exec(
        name, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=os.environ.copy(),
    )
    try:
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return "انتهت مهلة أداة Termux:API."
    text = output.decode("utf-8", errors="replace").strip()
    if proc.returncode:
        return f"فشلت {name} ({proc.returncode}): {text[-3000:]}"
    return text or "تم التنفيذ بلا مخرجات."


async def battery_status() -> str:
    return await _run("termux-battery-status")


async def toast(text: str, long: bool = False) -> str:
    if not text.strip():
        return "النص فارغ."
    return await _run("termux-toast", "-s" if not long else "-l", text[:2000])


async def notification(title: str, content: str) -> str:
    if not title.strip() or not content.strip():
        return "العنوان والمحتوى مطلوبان."
    return await _run("termux-notification", "--title", title[:200], "--content", content[:2000], "--id", "ai-phone-agent")


async def vibrate(duration_ms: Any = 300) -> str:
    try:
        duration = max(1, min(10000, int(duration_ms)))
    except (TypeError, ValueError):
        return "مدة الاهتزاز غير صالحة."
    return await _run("termux-vibrate", "-d", str(duration), "-f")


async def open_url(url: str) -> str:
    if not (url.startswith("https://") or url.startswith("http://")):
        return "يسمح فقط بروابط http وhttps."
    return await _run("termux-open-url", url[:2000])
