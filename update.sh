#!/usr/bin/env bash
# p3ta-tricks — update all sources and rebuild index
set -e
cd "$(dirname "$0")"

echo "[*] Pulling latest from all sources..."

for repo in sources/hacker-recipes sources/hacktricks sources/hacktricks-cloud sources/netexec-wiki; do
  if [ -d "$repo/.git" ]; then
    echo "    $repo"
    git -C "$repo" pull --ff-only --quiet
  else
    echo "    [!] $repo is not a git repo, skipping"
  fi
done

echo "[*] Rebuilding content index..."
python3 scripts/build.py

echo "[+] Done. Restart the server to serve updated content."
