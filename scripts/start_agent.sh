#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdir -p logs
termux-wake-lock 2>/dev/null || true
if [ -f agent.pid ] && kill -0 "$(cat agent.pid)" 2>/dev/null; then
  echo "agent already running: PID $(cat agent.pid)"
  exit 0
fi
nohup python -m agent.bot >> logs/agent.log 2>&1 &
echo $! > agent.pid
echo "agent started: PID $(cat agent.pid)"
