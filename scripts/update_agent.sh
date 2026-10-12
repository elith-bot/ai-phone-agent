#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/5] إيقاف الوكيل إن كان يعمل..."
./scripts/stop_agent.sh 2>/dev/null || true

echo "[2/5] جلب آخر نسخة من GitHub..."
git pull --ff-only origin main

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "تم إنشاء .env من القالب؛ أضف مفاتيحك قبل التشغيل."
fi

echo "[3/5] إضافة الإعدادات الجديدة مع الحفاظ على القيم الحالية..."
python - <<'PY'
from pathlib import Path

path = Path('.env')
values = {
    'STT_MODEL': 'whisper-large-v3-turbo',
    'MEDIA_TMP_DIR': str(Path.home() / 'ai_phone_agent' / 'data' / 'media'),
    'AGENT_EVENT_LOG': 'logs/events.jsonl',
    'MAX_PLAN_STEPS': '30',
    'PLAN_RETRIES': '1',
    'ADB_SERIAL': '',
    'ADB_COMMAND_TIMEOUT': '30',
    'VERIFY_AFTER_ADB': 'true',
    'ANDROID_ACCESS_URL': 'http://127.0.0.1:8765',
    'ANDROID_ACCESS_TIMEOUT': '15',
}
lines = path.read_text(encoding='utf-8').splitlines()
seen = set()
out = []
for line in lines:
    key = line.split('=', 1)[0].strip() if line and not line.lstrip().startswith('#') and '=' in line else ''
    if key in values:
        out.append(f'{key}={line.split("=", 1)[1]}')
        seen.add(key)
    else:
        out.append(line)
if out and out[-1] != '':
    out.append('')
for key, value in values.items():
    if key not in seen:
        out.append(f'{key}={value}')
path.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8')
path.chmod(0o600)
Path('data/media').mkdir(parents=True, exist_ok=True)
Path('logs').mkdir(parents=True, exist_ok=True)
PY

echo "[4/5] فحص الصياغة والاعتماديات..."
rm -rf agent/__pycache__
python -m compileall -q agent

if [ -d .venv ]; then
  source .venv/bin/activate
  python -m pip install -r requirements.txt
fi

echo "[5/5] تشغيل الوكيل بالخلفية..."
chmod +x scripts/*.sh
./scripts/start_agent.sh

echo "اكتمل التحديث والتشغيل. أرسل /status ثم /models للتحقق."
