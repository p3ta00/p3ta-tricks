#!/usr/bin/env python3
"""Recreate the search index exclusively from committed processed pages."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
entries = {}
for file in sorted((ROOT / "content" / "processed").glob("*/*.json")):
    try:
        page = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        continue
    source = page.get("source") or file.parent.name
    path = page.get("path") or file.stem.replace("__", "/")
    if not page.get("title") or not source or not path:
        continue
    key = (source, path)
    entries[key] = {
        "title": page["title"], "source": source,
        "url": f"/page/{source}/{path}", "path": path,
        "excerpt": page.get("excerpt", ""), "tags": page.get("tags", []),
    }
out = sorted(entries.values(), key=lambda x: (x["source"].casefold(), x["title"].casefold(), x["path"].casefold()))
(ROOT / "static" / "search_index.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Rebuilt {len(out)} unique search entries from processed pages")
