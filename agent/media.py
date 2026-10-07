import base64
import os
import subprocess
from pathlib import Path
import httpx

TMP_DIR = Path(os.getenv("MEDIA_TMP_DIR", str(Path.home() / "ai_phone_agent" / "data" / "media")))
TMP_DIR.mkdir(parents=True, exist_ok=True)

async def download_telegram_file(message, context, suffix: str) -> Path:
    obj = message.voice or message.audio or message.video or message.document or (message.photo[-1] if message.photo else None)
    tg_file = await context.bot.get_file(obj.file_id)
    path = TMP_DIR / f"telegram_{message.message_id}{suffix}"
    await tg_file.download_to_drive(custom_path=str(path))
    return path

async def groq_transcribe(path: Path) -> str:
    key = os.environ["GROQ_API_KEY"]
    data = {"model": os.getenv("STT_MODEL", "whisper-large-v3-turbo"), "response_format": "json", "language": "ar"}
    async with httpx.AsyncClient(timeout=180) as client:
        with path.open("rb") as file:
            response = await client.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {key}"}, data=data, files={"file": (path.name, file, "application/octet-stream")})
        response.raise_for_status()
    return response.json().get("text", "")

async def vision_answer(path: Path, prompt: str, provider: str, model: str) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode()
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    content = [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}]
    from .providers import ask_multimodal
    return await ask_multimodal(content, provider, model)

def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)[:30000]
    except ImportError:
        return "لم تُثبت pypdf بعد. نفّذ: pip install pypdf"
    except Exception as exc:
        return f"تعذر قراءة PDF: {exc}"

def video_frames(path: Path) -> list[Path]:
    out_dir = TMP_DIR / f"frames_{path.stem}"
    out_dir.mkdir(exist_ok=True)
    output = out_dir / "frame_%03d.jpg"
    subprocess.run(["ffmpeg", "-y", "-i", str(path), "-vf", "fps=1/10", "-frames:v", "6", str(output)], capture_output=True, timeout=120)
    return sorted(out_dir.glob("frame_*.jpg"))

async def web_search(query: str) -> str:
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "ai-phone-agent/1.0"}) as client:
        response = await client.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1})
        response.raise_for_status()
    data = response.json()
    rows = []
    if data.get("AbstractText"):
        rows.append(f"{data.get('Heading','')}: {data['AbstractText']} ({data.get('AbstractURL','')})")
    for item in data.get("RelatedTopics", [])[:8]:
        if isinstance(item, dict) and item.get("Text"):
            rows.append(f"{item['Text']} ({item.get('FirstURL','')})")
    return "\n".join(rows) or "لم تظهر نتائج مختصرة."
