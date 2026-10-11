from __future__ import annotations

import asyncio
import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from .events import AgentEvent, observation_event, tool_call_event
from .tool_registry import execute_tool

Progress = Callable[[int, int, str, str], Awaitable[None] | None]


def _event_log() -> Path:
    path = Path(os.getenv("AGENT_EVENT_LOG", "logs/events.jsonl")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_event(event: AgentEvent) -> None:
    # لا نسجل مفاتيح البيئة أو النصوص الكاملة للمدخلات الحساسة.
    with _event_log().open("a", encoding="utf-8") as handle:
        handle.write(event.to_json() + "\n")


def _failure_kind(result: str) -> str | None:
    value = result.casefold()
    if any(word in value for word in ("فشل", "خطأ", "تعذر", "غير متاح", "انتهت مهلة", "رفضت")):
        if "مهلة" in value:
            return "timeout"
        if "غير متاح" in value or "adb" in value and "فشل" in value:
            return "unavailable"
        if "صلاح" in value or "مسموح" in value:
            return "policy"
        return "tool_error"
    return None


def _safe_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    hidden = ("token", "key", "secret", "password", "authorization", "content")
    return {key: "[redacted]" if any(word in key.casefold() for word in hidden) else value for key, value in arguments.items()}


async def execute_plan(steps: list[dict[str, Any]], task_id: str, progress: Progress | None = None) -> list[dict[str, Any]]:
    max_steps = max(1, int(os.getenv("MAX_PLAN_STEPS", "30")))
    retries = max(0, int(os.getenv("PLAN_RETRIES", os.getenv("STEP_RETRIES", "1"))))
    if not steps or len(steps) > max_steps:
        raise ValueError(f"الخطة يجب أن تحتوي من خطوة إلى {max_steps} خطوة.")

    results: list[dict[str, Any]] = []
    total = len(steps)
    for index, raw in enumerate(steps, 1):
        tool = str(raw.get("tool", "")).strip()
        arguments = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else {}
        title = str(raw.get("title") or tool or f"الخطوة {index}")
        on_failure = str(raw.get("on_failure", "stop")).lower()
        if not tool:
            raise ValueError(f"الخطوة {index} لا تحتوي اسم أداة.")

        if progress:
            value = progress(index, total, title, "started")
            if inspect.isawaitable(value):
                await value
        _write_event(tool_call_event(task_id, tool, _safe_arguments(arguments)))

        result = ""
        failure = "tool_error"
        attempts = retries + 1
        for attempt in range(1, attempts + 1):
            try:
                result = await execute_tool(tool, arguments)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # الأداة لا توقف المهمة كلها بلا سجل واضح
                result = f"استثناء في الأداة: {exc}"
            failure = _failure_kind(result)
            if not failure or attempt == attempts:
                break
            if progress:
                value = progress(index, total, title, f"retry:{attempt + 1}/{attempts}")
                if inspect.isawaitable(value):
                    await value

        success = failure is None
        _write_event(observation_event(task_id, tool, result, success=success))
        item = {"index": index, "tool": tool, "title": title, "success": success, "attempts": attempts if failure else max(1, attempts - retries), "failure": failure, "result": result[-8000:]}
        results.append(item)
        if progress:
            value = progress(index, total, title, "done" if success else f"failed:{failure}")
            if inspect.isawaitable(value):
                await value
        if not success and on_failure not in {"continue", "skip"}:
            break
    return results
