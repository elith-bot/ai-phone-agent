import asyncio
import difflib
import fnmatch
import os
import tempfile
from pathlib import Path
from typing import Any
from .tools import phone_workspace, run_shell
from .termux_tools import battery_status, notification, open_url, toast, vibrate
from .accessibility_tools import (
    accessibility_back,
    accessibility_click,
    accessibility_health,
    accessibility_home,
    accessibility_snapshot,
    accessibility_type,
)
from .adb_tools import (
    adb_capabilities,
    adb_devices,
    adb_key,
    adb_open_app,
    adb_screenshot,
    adb_swipe,
    adb_tap,
    adb_type,
    ui_dump,
    ui_find,
)


def shared_root() -> Path:
    return Path(os.getenv("PHONE_STORAGE_ROOT", str(Path.home() / "storage" / "shared"))).expanduser().resolve()


def resolve_path(raw: str) -> Path:
    value = str(raw).strip()
    if value and not value.startswith(("/", "~")):
        value = str(phone_workspace() / value)
    storage_root = str(shared_root())
    value = value.replace("/storage/emulated/0", storage_root, 1)
    value = value.replace("/sdcard", storage_root, 1)
    value = value.replace("~/AI_Workspace", str(phone_workspace()), 1)
    if value.startswith("~/storage/shared/shared"):
        value = value.replace("~/storage/shared/shared", "~/storage/shared", 1)
    elif value.startswith("~/storage/") and not value.startswith("~/storage/shared"):
        value = value.replace("~/storage/", "~/storage/shared/", 1)
    path = Path(value).expanduser().resolve()
    roots = [Path(os.getenv("WORKSPACE_DIR", Path.home() / "agent-workspace")).expanduser().resolve(), phone_workspace(), shared_root()]
    if not any(path == root or root in path.parents for root in roots):
        raise ValueError("المسار خارج المساحات المسموحة")
    return path


def _text(value: Any) -> str:
    return str(value) if value is not None else ""


def _atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def _patch_file(arguments: dict[str, Any]) -> str:
    path = resolve_path(_text(arguments.get("path")))
    old_text = _text(arguments.get("old_text"))
    new_text = _text(arguments.get("new_text"))
    if not old_text:
        raise ValueError("old_text لا يمكن أن يكون فارغًا.")
    if not path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {path}")
    current = path.read_text(encoding="utf-8", errors="replace")
    occurrences = current.count(old_text)
    if occurrences != 1:
        raise ValueError(f"لم يتم التعديل: المقطع ظهر {occurrences} مرة؛ يجب أن يظهر مرة واحدة فقط.")
    updated = current.replace(old_text, new_text, 1)
    _atomic_write(path, updated)
    diff = "".join(difflib.unified_diff(current.splitlines(True), updated.splitlines(True), fromfile=str(path), tofile=str(path)))
    return f"تم تعديل الملف مباشرة دون إعادة كتابته كاملًا: {path}\nDiff:\n{diff[-6000:]}"


def _ensure_path_config() -> str:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    values = {
        "WORKSPACE_DIR": "/data/data/com.termux/files/home/agent-workspace",
        "PHONE_WORKSPACE_DIR": "/data/data/com.termux/files/home/storage/shared/AI_Workspace",
        "PHONE_STORAGE_ROOT": "/data/data/com.termux/files/home/storage/shared",
        "AGENT_MODE": "safe",
        "MAX_COMMAND_SECONDS": "0",
        "AI_REQUEST_TIMEOUT": "120",
        "TASK_HEARTBEAT_SECONDS": "20",
        "MESSAGE_DEBOUNCE_SECONDS": "2",
        "STEP_RETRIES": "1",
        "ADB_SERIAL": "",
        "ADB_COMMAND_TIMEOUT": "30",
        "ANDROID_ACCESS_URL": "http://127.0.0.1:8765",
        "ANDROID_ACCESS_TIMEOUT": "15",
    }
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = existing.splitlines()
    seen = set()
    output = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if line and not line.lstrip().startswith("#") and "=" in line else ""
        if key in values:
            output.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            output.append(line)
    if output and output[-1] != "":
        output.append("")
    for key, value in values.items():
        if key not in seen:
            output.append(f"{key}={value}")
    env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass
    phone_workspace().mkdir(parents=True, exist_ok=True)
    return f"تم تحديث إعدادات المسارات في {env_path} وإنشاء مجلد ملفات المستخدم: {phone_workspace()} دون تغيير مفاتيح API."


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "config.ensure_paths":
        return _ensure_path_config()
    if name == "adb.devices":
        return await adb_devices()
    if name == "adb.capabilities":
        return await adb_capabilities()
    if name == "adb.ui_dump":
        return await ui_dump()
    if name == "adb.ui_find":
        return await ui_find(_text(arguments.get("query")))
    if name == "adb.tap":
        return await adb_tap(_text(arguments.get("query")), _text(arguments.get("y")) or None)
    if name == "adb.screenshot":
        return await adb_screenshot(_text(arguments.get("path")))
    if name == "adb.open_app":
        return await adb_open_app(_text(arguments.get("package")))
    if name == "adb.swipe":
        return await adb_swipe(arguments.get("x1"), arguments.get("y1"), arguments.get("x2"), arguments.get("y2"), arguments.get("duration_ms", 400))
    if name == "adb.type":
        return await adb_type(_text(arguments.get("text")))
    if name == "adb.key":
        return await adb_key(arguments.get("keycode"))
    if name == "termux.battery":
        return await battery_status()
    if name == "termux.toast":
        return await toast(_text(arguments.get("text")), bool(arguments.get("long", False)))
    if name == "termux.notification":
        return await notification(_text(arguments.get("title")), _text(arguments.get("content")))
    if name == "termux.vibrate":
        return await vibrate(arguments.get("duration_ms", 300))
    if name == "termux.open_url":
        return await open_url(_text(arguments.get("url")))
    if name == "android.accessibility_health":
        return await accessibility_health()
    if name == "android.accessibility_snapshot":
        return await accessibility_snapshot()
    if name == "android.accessibility_click":
        return await accessibility_click(_text(arguments.get("query")))
    if name == "android.accessibility_type":
        return await accessibility_type(_text(arguments.get("text")))
    if name == "android.accessibility_back":
        return await accessibility_back()
    if name == "android.accessibility_home":
        return await accessibility_home()
    if name == "terminal.run":
        code, output = await run_shell(_text(arguments.get("command")))
        return f"النتيجة ({code}):\n{output or 'تم التنفيذ بلا مخرجات'}"
    if name in {"filesystem.create", "filesystem.update"}:
        path = resolve_path(_text(arguments.get("path")) or str(phone_workspace()))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_text(arguments.get("content")), encoding="utf-8")
        return f"تم {'إنشاء' if name.endswith('create') else 'تحديث'} الملف: {path}"
    if name == "filesystem.patch":
        return _patch_file(arguments)
    if name == "filesystem.read":
        path = resolve_path(_text(arguments.get("path")))
        return path.read_text(encoding="utf-8", errors="replace")[-12000:]
    if name == "filesystem.search":
        root = resolve_path(_text(arguments.get("path")) or str(phone_workspace()))
        pattern = _text(arguments.get("pattern", "*"))
        content = _text(arguments.get("content"))
        limit = max(1, min(int(arguments.get("limit", 200)), 500))
        newest = bool(arguments.get("newest", False))
        exclude_thumbnails = bool(arguments.get("exclude_thumbnails", True))
        found = []
        for path in root.rglob("*"):
            if not path.is_file() or not fnmatch.fnmatch(path.name, pattern):
                continue
            if exclude_thumbnails and ".thumbnails" in path.parts:
                continue
            if content:
                try:
                    if content not in path.read_text(encoding="utf-8", errors="ignore"):
                        continue
                except OSError:
                    continue
            found.append(str(path))
        if newest:
            found.sort(key=lambda item: Path(item).stat().st_mtime, reverse=True)
        found = found[:limit]
        return "\n".join(found) or "لا توجد نتائج."
    if name == "filesystem.delete":
        path = resolve_path(_text(arguments.get("path")))
        return f"DELETE_REQUIRES_APPROVAL:{path}"
    raise ValueError(f"أداة غير معروفة: {name}")
