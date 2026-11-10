#!/usr/bin/env bash
# Complete maintainer refresh: every reproducible content source, provenance,
# navigation, and search index. Binary releases are updated separately because
# their platform-specific assets require maintainer review.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PY="${PYTHON:-}"
for candidate in "$PWD/.venv/bin/python3" "$PWD/.venv/Scripts/python.exe" "$(command -v python3 || command -v python || true)"; do
  [ -n "$PY" ] && break
  [ -x "$candidate" ] && PY="$candidate"
done
[ -n "$PY" ] || { echo '[!] Python not found'; exit 1; }

# Refresh the ordinary Markdown/wiki sources through the fidelity-gated path.
PYTHON="$PY" bash ./update.sh --force "${@}"

# Clone or hard-reset supplemental repositories.
SUPPLEMENTAL=(
  'lolbas|https://github.com/LOLBAS-Project/LOLBAS.git'
  'wadcoms|https://github.com/WADComs/WADComs.github.io.git'
  'sliver|https://github.com/BishopFox/sliver.git'
  'exploitdb-new|https://gitlab.com/exploit-database/exploitdb.git'
)
for row in "${SUPPLEMENTAL[@]}"; do
  IFS='|' read -r directory url <<< "$row"
  path="sources/$directory"
  if [ ! -d "$path/.git" ]; then
    rm -rf "$path"
    git -c core.longpaths=true clone --quiet --depth 1 "$url" "$path"
  else
    branch=$(git -C "$path" branch --show-current)
    git -c core.longpaths=true -C "$path" fetch --quiet --depth 1 origin "$branch"
    git -c core.longpaths=true -C "$path" reset --quiet --hard "origin/$branch"
  fi
done

"$PY" scripts/fetch_adaptix_docs.py
"$PY" scripts/fetch_churchofmalware.py
"$PY" scripts/rebuild_supplemental.py
"$PY" scripts/rebuild_sources.py sliver adaptix
"$PY" scripts/rebuild_nav.py
"$PY" scripts/rebuild_search_index.py
"$PY" scripts/enhance_search_index.py
"$PY" scripts/local_fixes.py
"$PY" scripts/record_binary_provenance.py

echo '[+] Full source refresh complete.'
