#!/usr/bin/env python3
"""Rebuild the complete search index from committed processed page JSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "content" / "processed"
INDEX = ROOT / "static" / "search_index.json"


def main() -> int:
    entries = []
    seen_urls = {}
    for source_dir in sorted(path for path in PROCESSED.iterdir() if path.is_dir()):
        for page_file in sorted(source_dir.glob("*.json")):
            page = json.loads(page_file.read_text(encoding="utf-8"))
            source = str(page.get("source") or source_dir.name)
            path = str(page.get("path") or "").strip("/")
            title = str(page.get("title") or "").strip()
            if not path or not title:
                raise RuntimeError(f"Missing path/title in {page_file}")
            url = f"/page/{source}/{path}"
            if url in seen_urls:
                raise RuntimeError(f"Duplicate search URL {url}: {seen_urls[url]} and {page_file}")
            seen_urls[url] = str(page_file)
            entries.append({
                "title": title,
                "source": source,
                "url": url,
                "path": path,
                "excerpt": str(page.get("excerpt") or ""),
                "tags": page.get("tags") if isinstance(page.get("tags"), list) else [],
            })
    entries.sort(key=lambda item: (item["source"].lower(), item["title"].lower(), item["url"]))
    INDEX.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Rebuilt {len(entries)} unique search entries from processed pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
