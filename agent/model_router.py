import re
import time
from collections import defaultdict
from .model_catalog import ModelSpec, get_catalog

class ModelRouter:
    def __init__(self):
        self.used_today = defaultdict(int)
        self.used_minute = defaultdict(list)
        self.health = {item.key: True for item in get_catalog()}

    def classify(self, text: str, media: str | None = None) -> dict[str, object]:
        value = (text or "").lower()
        kind = media or "text"
        if not media:
            if any(x in value for x in ("صورة", "صوره", "image", "photo")): kind = "image"
            elif any(x in value for x in ("صوت", "بصمة", "audio", "voice")): kind = "audio"
            elif any(x in value for x in ("فيديو", "فديو", "video")): kind = "video"
            elif any(x in value for x in ("pdf", "ملف", "مستند")): kind = "pdf"
            elif any(x in value for x in ("ابحث", "بحث", "الويب", "web")): kind = "web"
        complexity = 1
        if len(text) > 1000 or any(x in value for x in ("حلل", "صمم", "برمج", "عدة خطوات", "معقد", "مشروع")): complexity += 2
        if any(x in value for x in ("احذف", "ثبت", "صلاحيات", "نظام")): complexity += 1
        return {"kind": kind, "complexity": min(complexity, 4), "length": len(text)}

    def choose(self, text: str, media: str | None = None, exclude: set[str] | None = None) -> tuple[ModelSpec, dict[str, object]]:
        info = self.classify(text, media)
        exclude = exclude or set()
        candidates = []
        for item in get_catalog():
            if item.key in exclude or not item.enabled or not self.health.get(item.key, True):
                continue
            if info["kind"] == "web":
                required = "text"
            else:
                required = str(info["kind"])
            if required not in item.capabilities:
                continue
            if item.daily_limit is not None and self.used_today[item.key] >= item.daily_limit:
                continue
            if item.rpm_limit is not None:
                now = time.time()
                self.used_minute[item.key] = [t for t in self.used_minute[item.key] if now - t < 60]
                if len(self.used_minute[item.key]) >= item.rpm_limit:
                    continue
            score = item.quality * 2 + item.speed + item.cost
            if info["complexity"] >= 3: score += item.quality
            if info["kind"] in item.strengths: score += 4
            candidates.append((score, item))
        if not candidates:
            raise RuntimeError("لا يوجد نموذج متاح حاليًا لهذا النوع من الطلب")
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        return candidates[0][1], info

    def mark_started(self, model: ModelSpec) -> None:
        self.used_today[model.key] += 1
        self.used_minute[model.key].append(time.time())

    def mark_health(self, model: ModelSpec, healthy: bool) -> None:
        self.health[model.key] = healthy

    def status(self) -> list[dict[str, object]]:
        rows = []
        for item in get_catalog():
            rows.append(item.public(self.used_today[item.key], len(self.used_minute[item.key]), self.health[item.key]))
        return rows
