import asyncio
import os
import re
from pathlib import Path

DELETE = re.compile(r"(^|[;&|()]|\s)(rm|rmdir|unlink|shred|truncate)\b|find\s+[^\n]*\s-delete\b|git\s+clean\s+-[a-z]*f", re.I)
HARD_BLOCK = re.compile(r"(^|[;&|])\s*(dd|mkfs|format|su|sudo|chmod\s+777|reboot|shutdown)\b|:\(\)\s*\{\s*:\|:&\s*\};:|curl[^|]*\|\s*(sh|bash)", re.I)


def workspace() -> Path:
    root = Path(os.getenv("WORKSPACE_DIR", Path.home() / "agent-workspace")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_command(command: str) -> str | None:
    command = command.strip()
    if not command or len(command) > 1000:
        return "الأمر فارغ أو طويل جدًا."
    if HARD_BLOCK.search(command):
        return "هذا الأمر محظور لحماية الهاتف."
    return None


def is_delete_command(command: str) -> bool:
    return bool(DELETE.search(command))


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
