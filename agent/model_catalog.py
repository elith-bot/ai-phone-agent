from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class ModelSpec:
    key: str
    provider: str
    model_id: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    capabilities: tuple[str, ...]
    quality: int
    speed: int
    cost: int
    daily_limit: int | None = None
    rpm_limit: int | None = None
    enabled: bool = True

    def public(self, used_today: int = 0, used_minute: int = 0, healthy: bool = True) -> dict[str, Any]:
        data = asdict(self)
        data.update({"used_today": used_today, "used_minute": used_minute, "healthy": healthy})
        return data


CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec("groq-qwen-vision", "groq", "qwen/qwen3.8-27b", ("text", "vision", "tools", "json"), ("video-direct",), ("text", "image", "tools"), 8, 10, 8),
    ModelSpec("groq-llama-fast", "groq", "llama-3.3-70b-versatile", ("text", "tools", "arabic"), ("vision", "audio", "video"), ("text", "tools"), 8, 10, 8),
    ModelSpec("groq-whisper", "groq", "whisper-large-v3-turbo", ("audio", "stt", "arabic"), ("chat",), ("audio", "stt"), 8, 10, 9),
    ModelSpec("openrouter-free", "openrouter", "openrouter/free", ("text", "variety", "fallback"), ("unstable-quota",), ("text", "image", "pdf", "audio", "video"), 7, 7, 10, daily_limit=50, rpm_limit=20),
    ModelSpec("gemini-flash", "gemini", "gemini-2.5-flash", ("text", "long-context", "files"), ("quota-429",), ("text", "image", "pdf", "video"), 8, 7, 7),
    ModelSpec("local-default", "local", "llama3.2", ("privacy", "offline"), ("speed", "quality"), ("text",), 5, 5, 10),
)


def get_catalog() -> list[ModelSpec]:
    return list(CATALOG)


def get_model(key: str) -> ModelSpec | None:
    return next((item for item in CATALOG if item.key == key), None)
