#!/usr/bin/env bash
# download_deps.sh — Download offline JS dependencies for p3ta-tricks
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JS_DIR="$SCRIPT_DIR/../static/js"

mkdir -p "$JS_DIR"

declare -A DEPS=(
  ["prism.min.js"]="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"
  ["prism-bash.min.js"]="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"
  ["prism-powershell.min.js"]="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-powershell.min.js"
  ["prism-python.min.js"]="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"
  ["prism-sql.min.js"]="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js"
  ["prism-csharp.min.js"]="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-csharp.min.js"
  ["fuse.min.js"]="https://cdnjs.cloudflare.com/ajax/libs/fuse.js/7.0.0/fuse.min.js"
)

echo "[*] Downloading JS dependencies to: $JS_DIR"
echo ""

for filename in "${!DEPS[@]}"; do
  url="${DEPS[$filename]}"
  dest="$JS_DIR/$filename"

  if [[ -f "$dest" ]]; then
    size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null || echo "?")
    echo "[~] Already exists: $filename (${size} bytes) — skipping"
    continue
  fi

  printf "[+] Downloading %-35s from %s\n" "$filename" "$url"
  if curl -fsSL --max-time 30 --retry 3 --retry-delay 2 -o "$dest" "$url"; then
    size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null || echo "?")
    echo "    => saved ${size} bytes"
  else
    echo "    [!] FAILED: $filename — check network connectivity"
    rm -f "$dest"
  fi
done

echo ""
echo "[*] Done. Files in $JS_DIR:"
ls -lh "$JS_DIR"/*.js 2>/dev/null || echo "    (no .js files found)"
