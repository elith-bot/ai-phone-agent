from __future__ import annotations

import asyncio
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .tools import phone_workspace


def _serial_args() -> list[str]:
    serial = os.getenv("ADB_SERIAL", "").strip()
    return ["-s", serial] if serial else []


def _timeout() -> float:
    return max(1.0, float(os.getenv("ADB_COMMAND_TIMEOUT", "30")))


async def _adb(*args: str, binary: bytes = False) -> tuple[int, str | bytes]:
    proc = await asyncio.create_subprocess_exec(
        "adb", *_serial_args(), *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=os.environ.copy(),
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=_timeout())
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        message = "انتهت مهلة أمر ADB."
        return 124, message.encode("utf-8") if binary else message
    if binary:
        return proc.returncode or 0, out
    return proc.returncode or 0, out.decode("utf-8", errors="replace").strip()


def _result(code: int, output: str | bytes, success: str = "تم التنفيذ.") -> str:
    if code != 0:
        text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output
        return f"فشل ADB ({code}): {text[-4000:]}"
    text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output
    return text or success


async def adb_devices() -> str:
    code, output = await _adb("devices", "-l")
    return _result(code, output, "لا توجد أجهزة متصلة.")


async def adb_capabilities() -> str:
    code, output = await _adb("shell", "getprop", "ro.build.version.release")
    if code != 0:
        return _result(code, output)
    version = str(output).strip()
    checks: dict[str, Any] = {"adb": True, "android_version": version, "serial": os.getenv("ADB_SERIAL", "") or "auto"}
    for name, args in {
        "shell": ("shell", "echo", "ok"),
        "screenshot": ("exec-out", "screencap", "-p"),
        "ui_dump": ("shell", "uiautomator", "dump", "/sdcard/agent_ui.xml"),
    }.items():
        probe_code, _ = await _adb(*args, binary=name == "screenshot")
        checks[name] = probe_code == 0
    return json.dumps(checks, ensure_ascii=False)


async def ui_dump() -> str:
    code, output = await _adb("shell", "uiautomator", "dump", "/sdcard/agent_ui.xml")
    if code != 0:
        return _result(code, output)
    code, output = await _adb("shell", "cat", "/sdcard/agent_ui.xml")
    return _result(code, output, "تمت قراءة واجهة الشاشة.")[-30000:]


def _center(bounds: str) -> tuple[int, int] | None:
    values = [int(v) for v in re.findall(r"\d+", bounds or "")]
    if len(values) != 4:
        return None
    return ((values[0] + values[2]) // 2, (values[1] + values[3]) // 2)


def _ui_matches(xml: str, query: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml)
    matches = []
    for node in root.iter():
        attrs = node.attrib
        haystack = " ".join(attrs.get(k, "") for k in ("text", "content-desc", "resource-id", "class"))
        if query.casefold() in haystack.casefold():
            matches.append({"text": attrs.get("text", ""), "description": attrs.get("content-desc", ""), "id": attrs.get("resource-id", ""), "bounds": attrs.get("bounds", ""), "center": _center(attrs.get("bounds", "")), "clickable": attrs.get("clickable", "false")})
    return matches[:30]


async def ui_find(query: str) -> str:
    if not query.strip():
        return "يجب تحديد نص أو معرف للبحث."
    xml = await ui_dump()
    try:
        matches = _ui_matches(xml, query)
    except ET.ParseError:
        return "تعذر تحليل XML لواجهة الشاشة."
    return json.dumps(matches, ensure_ascii=False) if matches else "لم أجد عنصرًا مطابقًا."


async def adb_tap(query_or_x: str, y: str | None = None) -> str:
    if y is None:
        found = await ui_find(query_or_x)
        try:
            match = json.loads(found)[0]
            x, yy = match["center"]
        except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
            return "لم أجد عنصرًا قابلًا للنقر."
    else:
        x, yy = int(query_or_x), int(y)
    code, output = await _adb("shell", "input", "tap", str(x), str(yy))
    return _result(code, output, "تم النقر.")


async def adb_screenshot(path: str = "") -> str:
    target = Path(path).expanduser() if path.strip() else phone_workspace() / "adb_screenshot.png"
    target = target.resolve()
    root = phone_workspace().resolve()
    if target != root and root not in target.parents:
        raise ValueError("مسار لقطة الشاشة يجب أن يكون داخل PHONE_WORKSPACE_DIR")
    target.parent.mkdir(parents=True, exist_ok=True)
    code, output = await _adb("exec-out", "screencap", "-p", binary=True)
    if code != 0:
        return _result(code, output)
    target.write_bytes(output if isinstance(output, bytes) else output.encode())
    return f"تم حفظ لقطة الشاشة: {target}"


async def adb_open_app(package: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.]+", package.strip()):
        return "اسم الحزمة غير صالح."
    code, output = await _adb("shell", "monkey", "-p", package.strip(), "1")
    return _result(code, output, f"تم فتح التطبيق: {package}")


async def adb_swipe(x1: Any, y1: Any, x2: Any, y2: Any, duration_ms: Any = 400) -> str:
    values = [int(x1), int(y1), int(x2), int(y2), max(1, int(duration_ms))]
    code, output = await _adb("shell", "input", "swipe", *(str(v) for v in values))
    return _result(code, output, "تم تنفيذ السحب.")


async def adb_type(text: str) -> str:
    if not text:
        return "النص فارغ."
    # input text لا يضمن Unicode على كل الأجهزة؛ يمنع المحارف التي تكسر argv.
    safe = text.replace("%", "%25").replace(" ", "%s").replace("&", "%26").replace(";", "%3B").replace("|", "%7C")
    code, output = await _adb("shell", "input", "text", safe[:2000])
    return _result(code, output, "تم إدخال النص.")


async def adb_key(keycode: Any) -> str:
    if not re.fullmatch(r"\d+", str(keycode)):
        return "يجب أن يكون keycode رقمًا."
    code, output = await _adb("shell", "input", "keyevent", str(keycode))
    return _result(code, output, "تم تنفيذ زر النظام.")
