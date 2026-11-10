#!/usr/bin/env python3
"""Export every page in the public Adaptix GitBook as Markdown.

GitBook exposes a stable llms.txt page inventory and Markdown endpoints. The
export is reproducible and records a digest of the inventory for provenance.
"""
from __future__ import annotations
import hashlib, json, re, shutil, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "adaptix"
INDEX_URL = "https://adaptix-framework.gitbook.io/adaptix-framework/llms.txt"
UA = "p3ta-tricks-maintainer/1.0"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/markdown,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def main():
    inventory = fetch(INDEX_URL)
    text = inventory.decode("utf-8")
    links = re.findall(r"^- \[([^]]+)]\((https://adaptix-framework\.gitbook\.io/adaptix-framework/[^)]+\.md)\)$", text, re.M)
    if len(links) < 50:
        raise SystemExit(f"refusing incomplete Adaptix inventory: {len(links)} pages")
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    summary = ["# Summary", ""]
    for title, url in links:
        rel = urlparse(url).path.removeprefix("/adaptix-framework/")
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = fetch(url)
        if len(body) < 20:
            raise RuntimeError(f"empty Adaptix page: {url}")
        dest.write_bytes(body)
        summary.append(f"* [{title}]({rel})")
    (OUT / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    meta = {
        "url": INDEX_URL,
        "branch": "GitBook public export",
        "commit": "sha256:" + hashlib.sha256(inventory).hexdigest(),
        "commit_time": datetime.now(timezone.utc).isoformat(),
        "page_count": len(links),
    }
    (OUT / ".source.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Exported {len(links)} Adaptix pages")

if __name__ == "__main__":
    main()
