import re
import xml.etree.ElementTree as ET
from .tools import run_shell

async def adb_devices() -> str:
    code, output = await run_shell("adb devices")
    return output if code == 0 else f"ADB غير متاح ({code}): {output}"

async def ui_dump() -> str:
    command = "adb shell uiautomator dump /sdcard/window_dump.xml >/dev/null 2>&1 && adb shell cat /sdcard/window_dump.xml"
    code, output = await run_shell(command)
    return output[-30000:] if code == 0 else f"فشل قراءة هيكل الشاشة ({code}): {output}"

def _center(bounds: str) -> tuple[int, int] | None:
    values = [int(v) for v in re.findall(r"\d+", bounds or "")]
    if len(values) != 4: return None
    return ((values[0] + values[2]) // 2, (values[1] + values[3]) // 2)

async def ui_find(query: str) -> str:
    xml = await ui_dump()
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return "تعذر تحليل XML لواجهة الشاشة."
    matches = []
    for node in root.iter():
        attrs = node.attrib
        haystack = " ".join(attrs.get(k, "") for k in ("text", "content-desc", "resource-id", "class"))
        if query.casefold() in haystack.casefold():
            center = _center(attrs.get("bounds", ""))
            matches.append({"text": attrs.get("text"), "description": attrs.get("content-desc"), "id": attrs.get("resource-id"), "bounds": attrs.get("bounds"), "center": center, "enabled": attrs.get("enabled")})
    return "\n".join(str(item) for item in matches[:30]) or "لم أجد عنصرًا مطابقًا."

async def adb_tap(query_or_x: str, y: str | None = None) -> str:
    if y is not None:
        x, yy = query_or_x, y
    else:
        found = await ui_find(query_or_x)
        match = re.search(r"'center': \((\d+), (\d+)\)", found)
        if not match: return "لم أجد عنصرًا قابلًا للنقر."
        x, yy = match.groups()
    code, output = await run_shell(f"adb shell input tap {int(x)} {int(yy)}")
    return output or ("تم النقر." if code == 0 else f"فشل النقر ({code}).")
