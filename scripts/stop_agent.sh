#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")/.."
if [ -f agent.pid ] && kill -0 "$(cat agent.pid)" 2>/dev/null; then
  kill "$(cat agent.pid)" || true
  rm -f agent.pid
  termux-wake-unlock 2>/dev/null || true
  echo "agent stopped"
else
  echo "agent is not running"
  rm -f agent.pid
fi
