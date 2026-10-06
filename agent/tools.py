import asyncio
import os
import re
from pathlib import Path

DANGEROUS = re.compile(r"(^|[;&|])\s*(rm|mv|dd|mkfs|format|su|sudo|chmod\s+777|reboot|shutdown)\b|>\s*/|curl[^|]*\|\s*(sh|bash)", re.I)


def workspace() -> Path:
    root = Path(os.getenv("WORKSPACE_DIR", Path.home() / "agent-workspace")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_command(command: str) -> str | None:
    command = command.strip()
    if not command or len(command) > 1000:
        return "الأمر فارغ أو طويل جدًا."
    if DANGEROUS.search(command):
        return "هذا الأمر مصنف كخطر ويحتاج مراجعة يدوية."
    return None


async def run_shell(command: str) -> tuple[int, str]:
    error = validate_command(command)
    if error:
        return 126, error
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=str(workspace()),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=os.environ.copy(),
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=int(os.getenv("MAX_COMMAND_SECONDS", "20")))
    except asyncio.TimeoutError:
        proc.kill()
        return 124, "انتهت مهلة الأمر."
    text = out.decode("utf-8", errors="replace")
    return proc.returncode or 0, text[-6000:]
