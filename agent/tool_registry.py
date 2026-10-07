import asyncio
import fnmatch
import os
from pathlib import Path
from typing import Any
from .tools import phone_workspace, run_shell
from .adb_tools import adb_devices, ui_dump, ui_find, adb_tap


def shared_root() -> Path:
    return Path(os.getenv("PHONE_STORAGE_ROOT", str(Path.home() / "storage" / "shared"))).expanduser().resolve()


def resolve_path(raw: str) -> Path:
    value = str(raw).strip()
    storage_root = str(shared_root())
    value = value.replace("/storage/emulated/0", storage_root, 1)
    value = value.replace("/sdcard", storage_root, 1)
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


def _ensure_path_config() -> str:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    values = {
        "WORKSPACE_DIR": "/data/data/com.termux/files/home/agent-workspace",
        "PHONE_WORKSPACE_DIR": "/data/data/com.termux/files/home/storage/shared/AI_Workspace",
        "PHONE_STORAGE_ROOT": "/data/data/com.termux/files/home/storage/shared",
        "AGENT_MODE": "safe",
        "MAX_COMMAND_SECONDS": "20",
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
    if name == "adb.ui_dump":
        return await ui_dump()
    if name == "adb.ui_find":
        return await ui_find(_text(arguments.get("query")))
    if name == "adb.tap":
        return await adb_tap(_text(arguments.get("query")), _text(arguments.get("y")) or None)
    if name == "terminal.run":
        code, output = await run_shell(_text(arguments.get("command")))
        return f"النتيجة ({code}):\n{output or 'تم التنفيذ بلا مخرجات'}"
    if name in {"filesystem.create", "filesystem.update"}:
        path = resolve_path(_text(arguments.get("path")) or str(phone_workspace()))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_text(arguments.get("content")), encoding="utf-8")
        return f"تم {'إنشاء' if name.endswith('create') else 'تحديث'} الملف: {path}"
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
