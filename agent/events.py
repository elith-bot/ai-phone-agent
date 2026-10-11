"""أحداث صغيرة قابلة للتسلسل لدورة الوكيل والأدوات."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import json
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AgentEvent:
    kind: str
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=_now)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


def request_event(task_id: str, text: str) -> AgentEvent:
    return AgentEvent("request", task_id=task_id, data={"text": text})


def tool_call_event(task_id: str, tool: str, arguments: dict[str, Any]) -> AgentEvent:
    return AgentEvent("tool_call", task_id=task_id, data={"tool": tool, "arguments": arguments})


def observation_event(task_id: str, tool: str, result: str, success: bool = True) -> AgentEvent:
    return AgentEvent("observation", task_id=task_id, data={"tool": tool, "success": success, "result": result})


def verification_event(task_id: str, passed: bool, reason: str) -> AgentEvent:
    return AgentEvent("verification", task_id=task_id, data={"passed": passed, "reason": reason})
