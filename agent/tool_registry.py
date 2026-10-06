import asyncio
import fnmatch
import os
from pathlib import Path
from typing import Any
from .tools import run_shell


def shared_root() -> Path:
    return (Path.home() / "storage" / "shared").resolve()


def resolve_path(raw: str) -> Path:
    value = str(raw).strip()
    if value.startswith("~/storage/") and not value.startswith("~/storage/shared/"):
        value = value.replace("~/storage/", "~/storage/shared/", 1)
    path = Path(value).expanduser().resolve()
    roots = [Path(os.getenv("WORKSPACE_DIR", Path.home() / "agent-workspace")).expanduser().resolve(), shared_root()]
    if not any(path == root or root in path.parents for root in roots):
        raise ValueError("المسار خارج المساحات المسموحة")
    return path


def _text(value: Any) -> str:
    return str(value) if value is not None else ""


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "terminal.run":
        code, output = await run_shell(_text(arguments.get("command")))
        return f"النتيجة ({code}):\n{output or 'تم التنفيذ بلا مخرجات'}"
    if name in {"filesystem.create", "filesystem.update"}:
        path = resolve_path(_text(arguments.get("path")))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_text(arguments.get("content")), encoding="utf-8")
        return f"تم {'إنشاء' if name.endswith('create') else 'تحديث'} الملف: {path}"
    if name == "filesystem.read":
        path = resolve_path(_text(arguments.get("path")))
        return path.read_text(encoding="utf-8", errors="replace")[-12000:]
    if name == "filesystem.search":
        root = resolve_path(_text(arguments.get("path", "~/storage/shared")))
        pattern = _text(arguments.get("pattern", "*"))
        content = _text(arguments.get("content"))
        found = []
        for path in root.rglob("*"):
            if not path.is_file() or not fnmatch.fnmatch(path.name, pattern):
                continue
            if content:
                try:
                    if content not in path.read_text(encoding="utf-8", errors="ignore"):
                        continue
                except OSError:
                    continue
            found.append(str(path))
            if len(found) >= 200:
                break
        return "\n".join(found) or "لا توجد نتائج."
    if name == "filesystem.delete":
        path = resolve_path(_text(arguments.get("path")))
        return f"DELETE_REQUIRES_APPROVAL:{path}"
    raise ValueError(f"أداة غير معروفة: {name}")
