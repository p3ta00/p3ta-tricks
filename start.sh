#!/usr/bin/env bash
# p3ta-tricks — offline pentest reference
# Usage: ./start.sh [--rebuild] [--port 5000]
set -e
cd "$(dirname "$0")"

PORT=5000
REBUILD=0
for arg in "$@"; do
  case "$arg" in
    --rebuild) REBUILD=1 ;;
    --port) PORT="$2" ;;
    --port=*) PORT="${arg#*=}" ;;
  esac
done

# Install deps if missing
if ! python3 -c "import flask" 2>/dev/null; then
  echo "[*] Installing Python dependencies..."
  pip install -r requirements.txt --break-system-packages -q
fi

# Build content index if missing or rebuild requested
if [ ! -f "static/search_index.json" ] || [ "$REBUILD" = "1" ]; then
  echo "[*] Building content index..."
  python3 scripts/build.py
fi

PAGES=$(python3 -c "import json; d=json.load(open('static/search_index.json')); print(len(d))" 2>/dev/null || echo "?")
echo "[+] p3ta-tricks running at http://localhost:${PORT}"
echo "[+] ${PAGES} pages indexed | Tokyo Night | Ctrl+K to search"
echo "[!] Press Ctrl+C to stop"
python3 -c "
import os; os.environ.setdefault('FLASK_ENV','production')
from app import app
app.run(host='0.0.0.0', port=${PORT}, debug=False, use_reloader=False)
"
