import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def db_path() -> Path:
    raw = os.getenv("MEMORY_DB_PATH", str(Path.home() / "ai_phone_agent" / "data" / "agent.sqlite3"))
    path = Path(raw).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            user_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_user_id_id ON messages(user_id, id);
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def add_message(user_id: int | str, role: str, content: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    uid = str(user_id)
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sessions(user_id, created_at, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at",
            (uid, now, now),
        )
        conn.execute("INSERT INTO messages(user_id, role, content, created_at) VALUES(?,?,?,?)", (uid, role, content[:12000], now))


def add_memory(user_id: int | str, content: str) -> None:
    if content.strip():
        with _conn() as conn:
            conn.execute("INSERT INTO memories(user_id, content, created_at) VALUES(?,?,?)", (str(user_id), content[:4000], datetime.now(timezone.utc).isoformat()))


def get_context(user_id: int | str, recent_limit: int = 24, memory_limit: int = 12) -> str:
    uid = str(user_id)
    with _conn() as conn:
        recent = conn.execute("SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, recent_limit)).fetchall()
        memories = conn.execute("SELECT content FROM memories WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, memory_limit)).fetchall()
    lines = ["ذاكرة طويلة الأمد:"] + [f"- {row[0]}" for row in reversed(memories)]
    lines += ["السياق الحديث:"] + [f"{role}: {content}" for role, content in reversed(recent)]
    return "\n".join(lines)[-14000:]


def stats(user_id: int | str) -> tuple[int, int]:
    with _conn() as conn:
        messages = conn.execute("SELECT COUNT(*) FROM messages WHERE user_id=?", (str(user_id),)).fetchone()[0]
        memories = conn.execute("SELECT COUNT(*) FROM memories WHERE user_id=?", (str(user_id),)).fetchone()[0]
    return messages, memories
