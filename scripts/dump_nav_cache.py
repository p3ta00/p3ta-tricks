#!/usr/bin/env python3
"""Freeze the sidebar nav tree for each source into content/nav/<source>.json.

app.py builds a source's nav by walking sources/<repo>, but only when there is
no pre-built JSON in content/nav/ -- that file always wins. Production (Railway)
has nothing else to go on, since sources/ is gitignored and never deployed, so
the cache has to be regenerated and committed whenever upstream content changes
or the sidebar silently keeps serving last month's tree.

Because the pre-built file short-circuits _get_nav(), this points app.py's cache
directory at an empty temp dir for the duration of the rebuild. That forces the
walk over sources/ while still reusing app.py's own tree-building logic, so the
two can't drift.

Usage:
    python3 scripts/dump_nav_cache.py                # every source with sources/ present
    python3 scripts/dump_nav_cache.py hacktricks     # named sources only
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402  (needs ROOT on sys.path first)

NAV_DIR = ROOT / "content" / "nav"


def build(source_id: str, empty_dir: Path):
    """Return the nav tree built from sources/, ignoring any cached JSON."""
    real_dir = app.NAV_CACHE_DIR
    app.NAV_CACHE_DIR = empty_dir
    app._nav_cache.pop(source_id, None)
    try:
        return app._get_nav(source_id)
    finally:
        app.NAV_CACHE_DIR = real_dir
        app._nav_cache.pop(source_id, None)


def dump(source_id: str, empty_dir: Path) -> str:
    cfg = app._NAV_SOURCES.get(source_id)
    if cfg and cfg.get("type") not in ("gtfobins", "lolbas") and not Path(cfg["root"]).exists():
        return "skip (sources/ not checked out)"

    tree = build(source_id, empty_dir)
    if not tree:
        return "skip (empty nav)"

    out = NAV_DIR / f"{source_id}.json"
    # indent=2 with no trailing newline, matching the committed files so an
    # unchanged tree produces no diff
    new = json.dumps(tree, ensure_ascii=False, indent=2)
    if out.exists() and out.read_text(encoding="utf-8") == new:
        return "unchanged"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(new, encoding="utf-8")
    return "written"


def main():
    targets = sys.argv[1:] or sorted(app._NAV_SOURCES)
    unknown = [t for t in targets if t not in app._NAV_SOURCES]
    if unknown:
        print(f"Unknown sources: {unknown}")
        print(f"Available: {sorted(app._NAV_SOURCES)}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as td:
        empty = Path(td)
        for sid in targets:
            print(f"  [{sid}] {dump(sid, empty)}")


if __name__ == "__main__":
    main()
