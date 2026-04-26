#!/usr/bin/env python3
"""Deduplication pass — run after build.py + add_content.py."""
import json, logging, re, sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR    = Path(__file__).parent.resolve()
PROJECT_DIR   = SCRIPT_DIR.parent
PROCESSED_DIR = PROJECT_DIR / "content" / "processed"
INDEX_PATH    = PROJECT_DIR / "static" / "search_index.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("dedup")

def _priority(path):
    for i, prefix in enumerate(["reference/","techniques/","cheatsheets/","resources/","tools/","notes/"]):
        if path.startswith(prefix): return i
    return 6

def _norm(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())

_ROMAN_RE = re.compile(r"\b(I{1,3}V?|VI{0,3}|IV|IX)\s*$", re.IGNORECASE)
def _has_roman(t): return bool(_ROMAN_RE.search(t.strip()))

_PRE_RE = re.compile(r"<pre[^>]*>.*?</pre>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE  = re.compile(r"\s+")

def _block_text(b): return _WS_RE.sub(" ", _TAG_RE.sub("", b)).strip()

def _merge(canon, dupe):
    have = {_block_text(b) for b in _PRE_RE.findall(canon["html"])}
    new  = [b for b in _PRE_RE.findall(dupe["html"])
            if _block_text(b) not in have and len(_block_text(b)) > 5]
    if new:
        canon["html"] += "\n" + "\n".join(new)
    for t in dupe.get("tags", []):
        if t not in canon.get("tags", []):
            canon.setdefault("tags", []).append(t)
    return canon

def _excerpt(html, n=300):
    t = _WS_RE.sub(" ", _TAG_RE.sub(" ", html)).strip()
    return t[:n].rsplit(" ", 1)[0] + "…" if len(t) > n else t

def _save(page):
    page["_file"].write_text(
        json.dumps({k:v for k,v in page.items() if k!="_file"}, ensure_ascii=False, indent=2),
        encoding="utf-8")

def main():
    pages = []
    for f in sorted(PROCESSED_DIR.rglob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            d["_file"] = f
            pages.append(d)
        except Exception:
            pass
    log.info("Loaded %d pages", len(pages))

    deleted = set()

    def do_merge(group):
        group.sort(key=lambda x: (_priority(x.get("path","")), x.get("title","")))
        canon = group[0]
        for dupe in group[1:]:
            if dupe["_file"] in deleted: continue
            if dupe.get("category") != canon.get("category"): continue
            log.info("  merge '%s' -> '%s'", dupe["title"], canon["title"])
            _merge(canon, dupe)
            deleted.add(dupe["_file"])
        canon["excerpt"] = _excerpt(canon["html"])
        _save(canon)

    # Pass 1: exact normalised title
    groups = defaultdict(list)
    for p in pages:
        groups[_norm(p.get("title",""))].append(p)
    for g in groups.values():
        if len(g) > 1:
            do_merge(g)

    # Pass 2: near-duplicates (substring, same category, no roman numeral distinction)
    surviving = [p for p in pages if p["_file"] not in deleted]
    norms = [(p, _norm(p["title"])) for p in surviving]
    used = set()
    for i,(pi,ni) in enumerate(norms):
        if i in used or len(ni) < 8: continue
        for j,(pj,nj) in enumerate(norms):
            if i>=j or j in used or len(nj) < 8: continue
            if pi.get("category") != pj.get("category"): continue
            if not (ni in nj or nj in ni): continue
            if _has_roman(pi["title"]) or _has_roman(pj["title"]): continue
            grp = sorted([pi,pj], key=lambda x:_priority(x.get("path","")))
            log.info("  near-merge '%s' -> '%s'", grp[1]["title"], grp[0]["title"])
            _merge(grp[0], grp[1])
            grp[0]["excerpt"] = _excerpt(grp[0]["html"])
            _save(grp[0])
            deleted.add(grp[1]["_file"])
            used.add(j)

    for f in deleted:
        f.unlink(missing_ok=True)
    log.info("Removed %d duplicates", len(deleted))

    # Rebuild index
    entries = []
    for i,f in enumerate(sorted(PROCESSED_DIR.rglob("*.json"))):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        entries.append({"id":i,"title":d.get("title",""),"category":d.get("category","misc"),
            "subcategory":d.get("subcategory",""),"path":d.get("path",""),
            "url":"/page/"+d.get("path",""),"excerpt":d.get("excerpt",""),"tags":d.get("tags",[])})
    INDEX_PATH.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    log.info("Index rebuilt: %d pages", len(entries))

if __name__ == "__main__":
    main()
