#!/usr/bin/env python3
"""p3ta-tricks Flask app — unified offline pentest reference."""
import json, re
from pathlib import Path
from flask import Flask, render_template, request, jsonify, abort

ROOT      = Path(__file__).parent
PROCESSED = ROOT / "content" / "processed"
INDEX     = ROOT / "static" / "search_index.json"
SOURCES   = ROOT / "sources"

app = Flask(__name__)

SOURCE_META = {
    "bloodhound":      {"label": "BloodHound",          "color": "var(--red)",     "icon": "🩸"},
    "hacker-recipes":  {"label": "The Hacker Recipes", "color": "var(--cyan)",    "icon": "🍳"},
    "hacktricks":      {"label": "HackTricks",          "color": "var(--red)",     "icon": "🤖"},
    "hacktricks-cloud":{"label": "HackTricks Cloud",    "color": "var(--blue)",    "icon": "☁️"},
    "netexec":         {"label": "NetExec Wiki",         "color": "var(--green)",   "icon": "🔧"},
    "gtfobins":        {"label": "GTFOBins",             "color": "var(--orange)",  "icon": "🐚"},
    "lolbas":          {"label": "LOLBAS",               "color": "var(--yellow)",  "icon": "🪟"},
    "msfvenom":        {"label": "msfvenom",             "color": "var(--purple)",  "icon": "💣"},
    "ligolo-ng":       {"label": "Ligolo-ng",            "color": "var(--teal)",    "icon": "🔀"},
    "certipy":         {"label": "Certipy",              "color": "var(--red)",     "icon": "📜"},
    "bloodyad":        {"label": "bloodyAD",             "color": "var(--crimson)", "icon": "🩸"},
    "patt":            {"label": "PayloadsAllTheThings", "color": "var(--orange)",  "icon": "💥"},
    "hardware-att":    {"label": "HardwareAllTheThings", "color": "var(--yellow)",  "icon": "🔌"},
    "internal-att":    {"label": "InternalAllTheThings", "color": "var(--purple)",  "icon": "🏰"},
    "goexec":          {"label": "goexec",               "color": "var(--green)",   "icon": "⚡"},
    "osai-research":   {"label": "OSAI Research",        "color": "var(--magenta)", "icon": "🤖"},
    "sliver":          {"label": "Sliver C2",             "color": "var(--red)",     "icon": "🐍"},
    "impacket":        {"label": "Impacket",              "color": "var(--cyan)",    "icon": "📦"},
    "gopacket":        {"label": "GoPacket",              "color": "var(--green)",   "icon": "🐹"},
    "rubeus":          {"label": "Rubeus",                "color": "var(--orange)",  "icon": "🎟️"},
    "mimikatz":        {"label": "Mimikatz",              "color": "var(--crimson)", "icon": "🐱"},
}

_NAV_SOURCES = {
    "hacker-recipes": {
        "root":    SOURCES / "hacker-recipes" / "docs" / "src",
        "summary": None,
        "skip_dirs":  {"assets", "contributing", ".vitepress"},
        "skip_files": {"index.md", "variables.md", "template.md", "ads.md", "donate.md"},
    },
    "hacktricks": {
        "root":    SOURCES / "hacktricks" / "src",
        "summary": SOURCES / "hacktricks" / "src" / "SUMMARY.md",
        "skip_dirs":  set(),
        "skip_files": {"SUMMARY.md", "LICENSE.md"},
    },
    "hacktricks-cloud": {
        "root":    SOURCES / "hacktricks-cloud" / "src",
        "summary": SOURCES / "hacktricks-cloud" / "src" / "SUMMARY.md",
        "skip_dirs":  set(),
        "skip_files": {"SUMMARY.md", "LICENSE.md"},
    },
    "netexec": {
        "root":    SOURCES / "netexec-wiki",
        "summary": SOURCES / "netexec-wiki" / "SUMMARY.md",
        "skip_dirs":  set(),
        "skip_files": {"SUMMARY.md", "logo-and-banner.md"},
    },
    "gtfobins": {
        "root":    SOURCES / "gtfobins" / "_gtfobins",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": set(),
        "type": "gtfobins",
    },
    "lolbas": {
        "root":    SOURCES / "lolbas" / "yml",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": set(),
        "type": "lolbas",
    },
    "msfvenom": {
        "root":    SOURCES / "msfvenom",
        "summary": SOURCES / "msfvenom" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    "ligolo-ng": {
        "root":    SOURCES / "ligolo-ng-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"_Sidebar.md", "_Footer.md"},
    },
    "certipy": {
        "root":    SOURCES / "certipy-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"_Footer.md", "format.py"},
    },
    "bloodyad": {
        "root":    SOURCES / "bloodyad-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"_Footer.md"},
    },
    "patt": {
        "root":    SOURCES / "payloadsallthethings",
        "summary": None,
        "skip_dirs": {"_LEARNING_AND_SOCIALS", "_template_vuln"},
        "skip_files": {"README.md", "CONTRIBUTING.md", "DISCLAIMER.md"},
        "readme_only": True,
    },
    "hardware-att": {
        "root":    SOURCES / "hardwareallthethings" / "docs",
        "summary": None,
        "skip_dirs": {"assets"},
        "skip_files": {"index.md"},
    },
    "internal-att": {
        "root":    SOURCES / "internalallthethings" / "docs",
        "summary": None,
        "skip_dirs": {"assets"},
        "skip_files": {"index.md"},
    },
    "goexec": {
        "root":    SOURCES / "goexec",
        "summary": None,
        "skip_dirs": {"cmd", "internal", "pkg"},
        "skip_files": set(),
    },
    "osai-research": {
        "root":    SOURCES / "osai-research",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"index.html", "README.md"},
    },
    "sliver": {
        "root":    SOURCES / "sliver-docs",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": set(),
    },
    "bloodhound": {
        "root":    SOURCES / "bloodhound",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": set(),
    },
    "impacket": {
        "root":    SOURCES / "impacket",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    "gopacket": {
        "root":    SOURCES / "gopacket-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"Home.md"},
    },
    "rubeus": {
        "root":    SOURCES / "rubeus",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    "mimikatz": {
        "root":    SOURCES / "mimikatz",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
}

_EMOJI_RE   = re.compile(r'[\U0001F000-\U0001FFFF‍ -⟿☀-⟿︀-﻿]+\s*')
_LINK_RE    = re.compile(r'^(\s*)[-*]\s+\[([^\]]+)\]\(([^)]+\.md)\)')
_SECTION_RE = re.compile(r'^#{1,3}\s+(.+)$')

_index_cache = None
_page_cache  = {}
_nav_cache   = {}


# ---------------------------------------------------------------------------
# Index / page loading
# ---------------------------------------------------------------------------
def _load_index():
    global _index_cache
    if _index_cache is None and INDEX.exists():
        _index_cache = json.loads(INDEX.read_text(encoding="utf-8"))
    return _index_cache or []


def _load_page(source: str, page_path: str):
    key = f"{source}/{page_path}"
    if key not in _page_cache:
        safe = page_path.replace("/", "__")
        candidates = list((PROCESSED / source).glob(f"{safe}.json"))
        if not candidates:
            candidates = list(PROCESSED.rglob(f"{safe}.json"))
        if not candidates:
            return None
        try:
            _page_cache[key] = json.loads(candidates[0].read_text(encoding="utf-8"))
        except Exception:
            return None
    return _page_cache.get(key)


def _search(q: str, limit: int = 30) -> list:
    if not q or len(q) < 2:
        return []
    idx = _load_index()
    ql  = q.lower()
    hits = []
    for entry in idx:
        title   = entry.get("title", "").lower()
        excerpt = entry.get("excerpt", "").lower()
        score   = 0
        if ql in title:          score += 10
        if title.startswith(ql): score += 5
        if ql in excerpt:        score += 2
        if score:
            hits.append((score, entry))
    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits[:limit]]


# ---------------------------------------------------------------------------
# Nav tree building
# ---------------------------------------------------------------------------
_ZWJ_RE = re.compile(r'[​-‏⁠﻿­]')

def _clean_title(t: str) -> str:
    t = _EMOJI_RE.sub('', t)
    t = _ZWJ_RE.sub('', t)
    return t.strip()


def _make_url(source_id: str, summary_path: Path, root: Path, rel: str) -> str:
    try:
        abs_path = (summary_path.parent / rel).resolve()
        rel_to_root = abs_path.relative_to(root)
        page_path = str(rel_to_root.with_suffix('')).replace('\\', '/').replace(' ', '-')
        page_path = re.sub(r'/README$', '', page_path)
        return f'/page/{source_id}/{page_path}'
    except Exception:
        return '#'


def _parse_flat_from_summary(source_id, cfg):
    summary_path = cfg['summary']
    root         = cfg['root']
    skip_files   = cfg['skip_files']
    flat = []

    for line in summary_path.read_text(encoding='utf-8').splitlines():
        sec_m = _SECTION_RE.match(line)
        if sec_m:
            title = _clean_title(sec_m.group(1))
            if title.lower() in ('summary', 'table of contents', ''):
                continue
            flat.append({'type': 'section', 'title': title.upper()})
            continue

        lnk_m = _LINK_RE.match(line)
        if lnk_m:
            indent = len(lnk_m.group(1))
            depth  = indent // 2
            title  = _clean_title(lnk_m.group(2))
            rel    = lnk_m.group(3).strip()
            if Path(rel).name in skip_files:
                continue
            url = _make_url(source_id, summary_path, root, rel)
            flat.append({'type': 'link', 'title': title, 'url': url, 'depth': depth})

    return flat


_H2_RE = re.compile(r'^##\s+(.+)$', re.MULTILINE)

def _parse_flat_from_dir(source_id, cfg):
    """Walk directory tree — sections = top-level dirs; root-level .md files get heading nav."""
    root       = cfg['root']
    skip_dirs  = cfg['skip_dirs']
    skip_files = cfg['skip_files']
    flat = []

    if not root.exists():
        return flat

    # readme_only mode (PATT-style): one README.md per top-level dir = one flat nav item
    if cfg.get('readme_only'):
        flat.append({'type': 'section', 'title': 'CONTENTS'})
        for top_dir in sorted(root.iterdir()):
            if not top_dir.is_dir():
                continue
            if top_dir.name in skip_dirs or top_dir.name.startswith('_') or top_dir.name.startswith('.'):
                continue
            if not (top_dir / "README.md").exists():
                continue
            title = top_dir.name  # preserve original spacing
            page_path = top_dir.name.replace(' ', '-').replace('\\', '/')
            flat.append({'type': 'link', 'title': title,
                         'url': f'/page/{source_id}/{page_path}', 'depth': 0})
        return flat

    top_dirs = sorted(
        (d for d in root.iterdir() if d.is_dir() and d.name not in skip_dirs),
        key=lambda d: d.name
    )

    for top_dir in top_dirs:
        flat.append({'type': 'section', 'title': top_dir.name.replace('-', ' ').upper()})
        for md in sorted(top_dir.rglob('*.md')):
            if md.name in skip_files:
                continue
            if any(part in skip_dirs for part in md.parts):
                continue
            rel_to_root = md.relative_to(root)
            depth = len(rel_to_root.parts) - 2
            page_path = str(rel_to_root.with_suffix('')).replace('\\', '/').replace(' ', '-')
            page_path = re.sub(r'/README$', '', page_path)
            title = md.stem.replace('-', ' ').replace('_', ' ').title()
            flat.append({'type': 'link', 'title': title,
                         'url': f'/page/{source_id}/{page_path}',
                         'depth': max(0, depth)})

    # Handle root-level .md files (e.g. msfvenom single-file source)
    root_mds = sorted(f for f in root.iterdir()
                      if f.is_file() and f.suffix == '.md' and f.name not in skip_files)
    for md in root_mds:
        page_path = str(md.relative_to(root).with_suffix('')).replace('\\', '/').replace(' ', '-')
        page_url  = f'/page/{source_id}/{page_path}'
        title     = md.stem.replace('-', ' ').replace('_', ' ').title()
        # Parse H2 headings to create sub-items with anchor links
        try:
            content = md.read_text(encoding='utf-8', errors='replace')
            h2s = _H2_RE.findall(content)
        except Exception:
            h2s = []
        if h2s:
            # Each H2 becomes a nav section containing the page link with anchor
            flat.append({'type': 'section', 'title': title.upper()})
            for h2 in h2s:
                anchor = re.sub(r'[^\w\s-]', '', h2.lower()).strip().replace(' ', '-')
                anchor = re.sub(r'-+', '-', anchor)
                flat.append({'type': 'link', 'title': h2.strip(),
                             'url': f'{page_url}#{anchor}', 'depth': 0})
        else:
            flat.append({'type': 'section', 'title': title.upper()})
            flat.append({'type': 'link', 'title': title, 'url': page_url, 'depth': 0})

    return flat


def _flat_to_tree(flat):
    """Convert flat list → [{type:section, title, items:[{title,url,children:[]}]}]"""
    sections = []
    cur_sec  = {'type': 'section', 'title': 'Contents', 'items': []}
    stack    = []  # (depth, node)

    for item in flat:
        if item['type'] == 'section':
            if cur_sec['items'] or sections:
                sections.append(cur_sec)
            cur_sec = {'type': 'section', 'title': item['title'], 'items': []}
            stack   = []
        else:
            depth = item.get('depth', 0)
            node  = {'title': item['title'], 'url': item['url'], 'children': []}

            # Pop stack to the right parent depth
            while stack and stack[-1][0] >= depth:
                stack.pop()

            if stack:
                stack[-1][1]['children'].append(node)
            else:
                cur_sec['items'].append(node)

            stack.append((depth, node))

    sections.append(cur_sec)
    return [s for s in sections if s['items']]


def _build_az_nav(source_id: str, entries: list) -> list:
    """Build A–Z sectioned nav from index entries for flat sources (GTFOBins, LOLBAS)."""
    from collections import defaultdict
    buckets = defaultdict(list)
    for e in sorted(entries, key=lambda x: x.get('title','').lower()):
        letter = e.get('title','?')[0].upper()
        if not letter.isalpha():
            letter = '#'
        buckets[letter].append({'title': e['title'], 'url': e['url'], 'children': []})
    sections = []
    for letter in sorted(buckets.keys()):
        sections.append({'type': 'section', 'title': letter, 'items': buckets[letter]})
    return sections


def _get_nav(source_id: str) -> list:
    if source_id in _nav_cache:
        return _nav_cache[source_id]

    cfg = _NAV_SOURCES.get(source_id)
    if not cfg:
        return []

    # GTFOBins and LOLBAS: build A–Z nav from index
    if cfg.get('type') in ('gtfobins', 'lolbas'):
        idx     = _load_index()
        entries = [e for e in idx if e.get('source') == source_id]
        tree    = _build_az_nav(source_id, entries)
        _nav_cache[source_id] = tree
        return tree

    if cfg['summary'] and cfg['summary'].exists():
        flat = _parse_flat_from_summary(source_id, cfg)
    else:
        flat = _parse_flat_from_dir(source_id, cfg)

    tree = _flat_to_tree(flat)

    if source_id == "bloodhound":
        tree.insert(0, {"type": "link", "title": "BloodHound Search", "url": "/source/bloodhound", "items": []})

    _nav_cache[source_id] = tree
    return tree


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    idx = _load_index()
    from collections import Counter
    counts = Counter(e.get("source", "") for e in idx)
    sources = []
    for sid, meta in SOURCE_META.items():
        sources.append({**meta, "id": sid, "count": counts.get(sid, 0)})
    return render_template("index.html", sources=sources, total=len(idx))


@app.route("/search")
def search():
    q       = request.args.get("q", "").strip()
    source  = request.args.get("source", "")
    fmt     = request.args.get("format", "")
    results = _search(q)
    if source:
        results = [r for r in results if r.get("source") == source]
    if fmt == "json" or request.accept_mimetypes.best == "application/json":
        return jsonify(results)
    return render_template("search.html", q=q, results=results,
                           source_meta=SOURCE_META, source_filter=source)


@app.route("/source/<source_id>")
def source_index(source_id):
    if source_id not in SOURCE_META:
        abort(404)
    idx  = _load_index()
    entries = [e for e in idx if e.get("source") == source_id]
    meta = SOURCE_META[source_id]
    if source_id == "gtfobins":
        # Collect all unique func: and ctx: tags for filter buttons
        all_tags = sorted({t for e in entries for t in e.get("tags", [])})
        return render_template("gtfobins_source.html", source_id=source_id, meta=meta,
                               entries=entries, all_tags=all_tags, source_meta=SOURCE_META)

    if source_id == "lolbas":
        all_tags = sorted({t for e in entries for t in e.get("tags", [])})
        return render_template("lolbas_source.html", source_id=source_id, meta=meta,
                               entries=entries, all_tags=all_tags, source_meta=SOURCE_META)

    if source_id == "bloodhound":
        edge_count = sum(1 for e in entries if "/edges/" in e.get("url", ""))
        collector_count = sum(1 for e in entries if "/collectors/" in e.get("url", ""))
        # Preload all page HTML so the search page can render content inline
        pages = {}
        for e in entries:
            page_path = e.get("path", "")
            data = _load_page("bloodhound", page_path)
            if data:
                pages[e["title"]] = data["html"]
        return render_template("bloodhound_source.html", source_id=source_id, meta=meta,
                               entries=entries, edge_count=edge_count,
                               collector_count=collector_count, pages=pages,
                               source_meta=SOURCE_META)

    return render_template("source.html", source_id=source_id, meta=meta,
                           entries=entries, source_meta=SOURCE_META)


@app.route("/page/<source_id>/<path:page_path>")
def page(source_id, page_path):
    if source_id not in SOURCE_META:
        abort(404)
    data = _load_page(source_id, page_path)
    if data is None:
        abort(404)
    meta = SOURCE_META[source_id]
    return render_template("page.html", page=data, meta=meta, source_meta=SOURCE_META)


@app.route("/api/index")
def api_index():
    source = request.args.get("source", "")
    idx    = _load_index()
    if source:
        idx = [e for e in idx if e.get("source") == source]
    return jsonify(idx)


@app.route("/api/nav/<source_id>")
def api_nav(source_id):
    if source_id not in SOURCE_META:
        abort(404)
    return jsonify(_get_nav(source_id))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
