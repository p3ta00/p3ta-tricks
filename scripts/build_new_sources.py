#!/usr/bin/env python3
"""Build content/processed JSON and search index for new sources."""
import json, re, sys
from pathlib import Path
import markdown as md_lib

ROOT      = Path(__file__).parent.parent
SOURCES   = ROOT / "sources"
PROCESSED = ROOT / "content" / "processed"
NAV_DIR   = ROOT / "content" / "nav"
INDEX     = ROOT / "static" / "search_index.json"

MD = md_lib.Markdown(extensions=[
    "fenced_code", "tables", "toc", "attr_list",
    "pymdownx.superfences", "pymdownx.highlight",
])

SOURCE_LABELS = {
    "enum":       "Enumeration",
    "revshells":  "Reverse Shells",
    "bug-bounty": "Bug Bounty",
}

NEW_SOURCES = {
    "enum": {
        "root":    SOURCES / "enum",
        "summary": SOURCES / "enum" / "SUMMARY.md",
        "skip":    {"SUMMARY.md"},
    },
    "revshells": {
        "root":    SOURCES / "revshells",
        "summary": SOURCES / "revshells" / "SUMMARY.md",
        "skip":    {"SUMMARY.md"},
    },
    "bug-bounty": {
        "root":    SOURCES / "bug-bounty",
        "summary": SOURCES / "bug-bounty" / "SUMMARY.md",
        "skip":    {"SUMMARY.md", "README.md"},
    },
}

_LINK_RE = re.compile(r'^\s*[-*]\s+\[([^\]]+)\]\(([^)]+\.md)\)', re.M)


def _md_to_html(text: str) -> str:
    MD.reset()
    return MD.convert(text)


def _excerpt(html: str, n: int = 200) -> str:
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:n]


def _slug(path_str: str) -> str:
    return Path(path_str).stem.replace(" ", "-").replace("_", "-").lower()


def build_source(source_id: str, cfg: dict) -> list:
    root    = cfg["root"]
    summary = cfg.get("summary")
    skip    = cfg.get("skip", set())

    if not root.exists():
        print(f"  SKIP {source_id}: source dir missing")
        return []

    out_dir = PROCESSED / source_id
    out_dir.mkdir(parents=True, exist_ok=True)

    label   = SOURCE_LABELS.get(source_id, source_id)
    entries = []

    # Collect files from SUMMARY or directory scan
    if summary and summary.exists():
        text = summary.read_text(encoding="utf-8", errors="ignore")
        files = []
        for m in _LINK_RE.finditer(text):
            title, rel = m.group(1).strip(), m.group(2).strip()
            fpath = root / rel
            if fpath.exists():
                files.append((title, fpath))
    else:
        files = []
        for f in sorted(root.rglob("*.md")):
            if f.name in skip:
                continue
            files.append((f.stem.replace("-", " ").replace("_", " ").title(), f))

    for title, fpath in files:
        if fpath.name in skip:
            continue
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        html = _md_to_html(text)
        rel  = fpath.relative_to(root)
        # page_path used in URL: /page/source_id/<page_path>
        page_path = str(rel).replace("\\", "/").removesuffix(".md")

        # JSON key: replace path separators with __
        safe_key = page_path.replace("/", "__").replace(" ", "-")

        page_data = {
            "title":        title,
            "source":       source_id,
            "source_label": label,
            "path":         page_path,
            "html":         html,
            "excerpt":      _excerpt(html),
            "tags":         [],
        }

        out_file = out_dir / f"{safe_key}.json"
        out_file.write_text(json.dumps(page_data, ensure_ascii=False), encoding="utf-8")

        entries.append({
            "title":   title,
            "source":  source_id,
            "url":     f"/page/{source_id}/{page_path}",
            "path":    page_path,
            "excerpt": page_data["excerpt"],
        })
        print(f"  + {source_id}/{page_path}")

    return entries


def build_nav(source_id: str, cfg: dict, entries: list) -> None:
    summary = cfg.get("summary")
    root    = cfg["root"]
    nav     = []

    if summary and summary.exists():
        text    = summary.read_text(encoding="utf-8", errors="ignore")
        section = {"type": "section", "title": SOURCE_LABELS.get(source_id, source_id).upper(), "items": []}
        for m in _LINK_RE.finditer(text):
            title, rel = m.group(1).strip(), m.group(2).strip()
            page_path = rel.removesuffix(".md")
            section["items"].append({"title": title, "url": f"/page/{source_id}/{page_path}", "children": []})
        nav.append(section)
    else:
        section = {"type": "section", "title": SOURCE_LABELS.get(source_id, source_id).upper(), "items": []}
        for e in entries:
            section["items"].append({"title": e["title"], "url": e["url"], "children": []})
        nav.append(section)

    NAV_DIR.mkdir(parents=True, exist_ok=True)
    (NAV_DIR / f"{source_id}.json").write_text(json.dumps(nav, ensure_ascii=False), encoding="utf-8")


def main():
    # Load existing search index
    existing = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []
    # Remove old entries for sources we're rebuilding
    existing = [e for e in existing if e.get("source") not in NEW_SOURCES]

    new_entries = []
    for sid, cfg in NEW_SOURCES.items():
        print(f"\n[{sid}]")
        entries = build_source(sid, cfg)
        build_nav(sid, cfg, entries)
        new_entries.extend(entries)
        print(f"  → {len(entries)} pages")

    combined = existing + new_entries
    INDEX.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSearch index: {len(combined)} total entries (+{len(new_entries)} new)")


if __name__ == "__main__":
    main()
