#!/usr/bin/env python3
"""
p3ta-tricks build script — processes all source repos into searchable content.
Sources: The Hacker Recipes, HackTricks, HackTricks Cloud, NetExec Wiki,
         GTFOBins, LOLBAS, msfvenom
"""
import json, logging, re, time, html as html_lib
from pathlib import Path
from multiprocessing import Pool, cpu_count

try:
    import markdown
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.codehilite import CodeHiliteExtension
    from markdown.extensions.toc import TocExtension
    import pymdownx.superfences  # noqa: F401  — ensures it's available
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable,"-m","pip","install","markdown","pymdown-extensions","Pygments","-q","--break-system-packages"])
    import markdown
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.codehilite import CodeHiliteExtension
    from markdown.extensions.toc import TocExtension

try:
    import yaml
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable,"-m","pip","install","pyyaml","-q","--break-system-packages"])
    import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("build")

ROOT         = Path(__file__).parent.parent
SOURCES      = ROOT / "sources"
PROCESSED    = ROOT / "content" / "processed"
INDEX_PATH   = ROOT / "static" / "search_index.json"
PROCESSED.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Markdown source definitions (summary-based or directory-walk)
# ---------------------------------------------------------------------------
SOURCES_DEF = [
    {
        "id":      "bloodhound",
        "label":   "BloodHound",
        "root":    SOURCES / "bloodhound",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": set(),
    },
    {
        "id":      "hacker-recipes",
        "label":   "The Hacker Recipes",
        "root":    SOURCES / "hacker-recipes" / "docs" / "src",
        "summary": None,
        "skip_dirs": {"assets","contributing",".vitepress"},
        "skip_files": {"index.md","variables.md","template.md","ads.md","donate.md"},
    },
    {
        "id":      "hacktricks",
        "label":   "HackTricks",
        "root":    SOURCES / "hacktricks" / "src",
        "summary": SOURCES / "hacktricks" / "src" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md","LICENSE.md"},
    },
    {
        "id":      "hacktricks-cloud",
        "label":   "HackTricks Cloud",
        "root":    SOURCES / "hacktricks-cloud" / "src",
        "summary": SOURCES / "hacktricks-cloud" / "src" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md","LICENSE.md"},
    },
    {
        "id":      "netexec",
        "label":   "NetExec Wiki",
        "root":    SOURCES / "netexec-wiki",
        "summary": SOURCES / "netexec-wiki" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md","logo-and-banner.md"},
    },
    {
        "id":      "msfvenom",
        "label":   "msfvenom",
        "root":    SOURCES / "msfvenom",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    {
        "id":      "ligolo-ng",
        "label":   "Ligolo-ng",
        "root":    SOURCES / "ligolo-ng-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"_Sidebar.md", "_Footer.md"},
    },
    {
        "id":      "certipy",
        "label":   "Certipy",
        "root":    SOURCES / "certipy-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"_Footer.md", "format.py"},
    },
    {
        "id":      "bloodyad",
        "label":   "bloodyAD",
        "root":    SOURCES / "bloodyad-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"_Footer.md"},
    },
    {
        "id":      "patt",
        "label":   "PayloadsAllTheThings",
        "root":    SOURCES / "payloadsallthethings",
        "summary": None,
        "skip_dirs": {"_LEARNING_AND_SOCIALS", "_template_vuln"},
        "skip_files": {"README.md", "CONTRIBUTING.md", "DISCLAIMER.md"},
        "readme_only": True,
    },
    {
        "id":      "hardware-att",
        "label":   "HardwareAllTheThings",
        "root":    SOURCES / "hardwareallthethings" / "docs",
        "summary": None,
        "skip_dirs": {"assets"},
        "skip_files": {"index.md"},
    },
    {
        "id":      "internal-att",
        "label":   "InternalAllTheThings",
        "root":    SOURCES / "internalallthethings" / "docs",
        "summary": None,
        "skip_dirs": {"assets"},
        "skip_files": {"index.md"},
    },
    {
        "id":      "goexec",
        "label":   "goexec",
        "root":    SOURCES / "goexec",
        "summary": None,
        "skip_dirs": {"cmd", "internal", "pkg"},
        "skip_files": set(),
    },
    {
        "id":      "osai-research",
        "label":   "OSAI Research",
        "root":    SOURCES / "osai-research",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"index.html", "README.md"},
    },
    {
        "id":      "sliver",
        "label":   "Sliver C2",
        "root":    SOURCES / "sliver-docs",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": set(),
    },
    {
        "id":      "impacket",
        "label":   "Impacket",
        "root":    SOURCES / "impacket",
        "summary": SOURCES / "impacket" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    {
        "id":      "gopacket",
        "label":   "GoPacket",
        "root":    SOURCES / "gopacket-wiki",
        "summary": None,
        "skip_dirs": set(),
        "skip_files": {"Home.md"},
    },
    {
        "id":      "rubeus",
        "label":   "Rubeus",
        "root":    SOURCES / "rubeus",
        "summary": SOURCES / "rubeus" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    {
        "id":      "mimikatz",
        "label":   "Mimikatz",
        "root":    SOURCES / "mimikatz",
        "summary": SOURCES / "mimikatz" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
]

# ---------------------------------------------------------------------------
# Nav parsing from SUMMARY.md
# ---------------------------------------------------------------------------
_SUMMARY_LINK = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')

def parse_summary(summary_path: Path, root: Path) -> list[dict]:
    items = []
    if not summary_path or not summary_path.exists():
        return items
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        m = _SUMMARY_LINK.search(line)
        if not m:
            continue
        title = m.group(1).strip()
        rel   = m.group(2).strip()
        depth = (len(line) - len(line.lstrip(" *-"))) // 2
        abs_path = (summary_path.parent / rel).resolve()
        if abs_path.exists():
            items.append({"title": title, "path": abs_path, "rel": rel, "depth": depth})
    return items

# ---------------------------------------------------------------------------
# Markdown pre-processing
# ---------------------------------------------------------------------------
_IMAGE_RE    = re.compile(r'!\[[^\]]*\]\([^)]+\)')
_FIGCAP_RE   = re.compile(r'<figure>.*?</figure>', re.DOTALL | re.IGNORECASE)

_ADMON_MAP = {
    "NOTE": ("note", "📝 Note"),
    "TIP": ("tip", "💡 Tip"),
    "SUCCESS": ("success", "✅"),
    "INFO": ("info", "ℹ️ Info"),
    "WARNING": ("warning", "⚠️ Warning"),
    "DANGER": ("danger", "🚨 Danger"),
    "CAUTION": ("danger", "⚠️ Caution"),
    "HINT": ("tip", "💡 Hint"),
    "EXAMPLE": ("info", "📋 Example"),
}

_GFM_ALERT_RE = re.compile(
    r'^>\s*\[!(NOTE|TIP|SUCCESS|INFO|WARNING|DANGER|CAUTION|HINT|EXAMPLE)\]\s*\n((?:>.*\n?)*)',
    re.MULTILINE | re.IGNORECASE
)
_VITEPRESS_ADMON_RE = re.compile(
    r'^:::\s*(info|tip|warning|danger|note|success|caution)\s*(?:[^\n]*)?\n(.*?)^:::',
    re.MULTILINE | re.DOTALL | re.IGNORECASE
)

def _admon_repl(m):
    kind = m.group(1).upper()
    body_lines = [l[1:].lstrip() if l.startswith('>') else l for l in m.group(2).splitlines()]
    body = '\n'.join(body_lines).strip()
    css, label = _ADMON_MAP.get(kind, ("info", kind.title()))
    return f'\n<div class="admonition admonition-{css}"><div class="admonition-title">{label}</div>\n\n{body}\n\n</div>\n'

def _vitepress_admon_repl(m):
    kind = m.group(1).lower()
    body = m.group(2).strip()
    css, label = _ADMON_MAP.get(kind.upper(), ("info", kind.title()))
    return f'\n<div class="admonition admonition-{css}"><div class="admonition-title">{label}</div>\n\n{body}\n\n</div>\n'

def _make_link_rewriter(source_id: str, file_path: Path, root: Path):
    def repl(m):
        text = m.group(1)
        target = m.group(2)
        if target.startswith(('http://','https://','mailto:','#')):
            return m.group(0)
        try:
            abs_target = (file_path.parent / target).resolve()
            rel_to_root = abs_target.relative_to(root)
            page_path = str(rel_to_root.with_suffix('')).replace('\\','/')
            page_path = re.sub(r'/README$', '', page_path)
            return f'[{text}](/page/{source_id}/{page_path})'
        except Exception:
            return f'[{text}](#)'
    return repl

_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

def preprocess(text: str, source_id: str, file_path: Path, root: Path) -> str:
    text = _IMAGE_RE.sub('', text)
    text = _FIGCAP_RE.sub('', text)
    text = _GFM_ALERT_RE.sub(_admon_repl, text)
    text = _VITEPRESS_ADMON_RE.sub(_vitepress_admon_repl, text)
    rewriter = _make_link_rewriter(source_id, file_path, root)
    text = _MD_LINK_RE.sub(rewriter, text)
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)
    text = re.sub(r'^\+\+\+\n.*?\n\+\+\+\n', '', text, flags=re.DOTALL)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    return text

# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------
def make_md():
    return markdown.Markdown(extensions=[
        TableExtension(),
        'pymdownx.superfences',       # handles indented fenced blocks in lists
        CodeHiliteExtension(guess_lang=True, css_class="highlight"),
        TocExtension(permalink=False),
        'nl2br',
    ], extension_configs={
        'pymdownx.superfences': {
            'disable_indented_code_blocks': False,
        },
    }, output_format="html")

# ---------------------------------------------------------------------------
# Title / excerpt helpers
# ---------------------------------------------------------------------------
_H1_RE  = re.compile(r'^#\s+(.+)$', re.MULTILINE)
_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE  = re.compile(r'\s+')

def extract_title(text: str, stem: str) -> str:
    m = _H1_RE.search(text)
    if m:
        t = re.sub(r'^[\U0001F000-\U0001FFFF☀-⟿︀-﻿\s]+', '', m.group(1).strip()).strip()
        return t or stem
    return stem.replace('-',' ').replace('_',' ').title()

def excerpt(html: str, n: int = 250) -> str:
    t = _WS_RE.sub(' ', _TAG_RE.sub(' ', html)).strip()
    return t[:n].rsplit(' ',1)[0]+'…' if len(t)>n else t

def _save_page(source_id, label, page_path, title, body_html, tags=None):
    ex = excerpt(body_html)
    tags = tags or []
    out = {
        "title": title, "source": source_id, "source_label": label,
        "path": page_path, "html": body_html, "excerpt": ex, "tags": tags,
    }
    out_file = PROCESSED / source_id / f"{page_path.replace('/','__')}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return {"title": title, "source": source_id, "source_label": label,
            "path": page_path, "url": f"/page/{source_id}/{page_path}", "excerpt": ex, "tags": tags}

# ---------------------------------------------------------------------------
# Markdown file worker (for existing 4 sources + msfvenom)
# ---------------------------------------------------------------------------
def process_file(args):
    source_id, label, md_path, root, page_path = args
    try:
        raw = md_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None
    text = preprocess(raw, source_id, md_path, root)
    title = extract_title(text, md_path.stem)
    md = make_md()
    try:
        body_html = md.convert(text)
    except Exception:
        return None
    if not body_html.strip():
        return None
    return _save_page(source_id, label, page_path, title, body_html)

# ---------------------------------------------------------------------------
# GTFOBins processor (YAML files, no extension)
# ---------------------------------------------------------------------------
_FUNC_LABELS = {
    "shell":                     "Shell",
    "reverse-shell":             "Reverse Shell",
    "bind-shell":                "Bind Shell",
    "non-interactive-shell":     "Non-Interactive Shell",
    "non-interactive-reverse-shell": "Non-Interactive Reverse Shell",
    "non-interactive-bind-shell":"Non-Interactive Bind Shell",
    "file-read":                 "File Read",
    "file-write":                "File Write",
    "file-upload":               "File Upload",
    "file-download":             "File Download",
    "library-load":              "Library Load",
    "command":                   "Command Execution",
    "sudo":                      "Sudo",
    "suid":                      "SUID",
    "capabilities":              "Capabilities",
    "limited-suid":              "Limited SUID",
}

def _gtfobins_entry_html(name: str, data: dict) -> str:
    parts = [f'<h1>{html_lib.escape(name)}</h1>']
    funcs = data.get('functions') or {}
    if not funcs:
        return ''
    for func_key, entries in funcs.items():
        label = _FUNC_LABELS.get(func_key, func_key.replace('-',' ').title())
        parts.append(f'<h2>{html_lib.escape(label)}</h2>')
        if not entries:
            continue
        for entry in (entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                continue
            comment = entry.get('comment','')
            code    = entry.get('code','')
            contexts = entry.get('contexts',{}) or {}
            if comment:
                parts.append(f'<p>{html_lib.escape(str(comment))}</p>')
            if code:
                parts.append(f'<pre><code class="language-bash">{html_lib.escape(str(code))}</code></pre>')
            # Render sudo/suid context overrides
            for ctx_name, ctx_val in contexts.items():
                if isinstance(ctx_val, dict) and ctx_val.get('code'):
                    ctx_code = ctx_val['code']
                    ctx_comment = ctx_val.get('comment','')
                    parts.append(f'<p><strong>{html_lib.escape(ctx_name.upper())} override:</strong></p>')
                    if ctx_comment:
                        parts.append(f'<p>{html_lib.escape(str(ctx_comment))}</p>')
                    parts.append(f'<pre><code class="language-bash">{html_lib.escape(str(ctx_code))}</code></pre>')
    return '\n'.join(parts)

def process_gtfobins():
    gtfo_dir = SOURCES / "gtfobins" / "_gtfobins"
    if not gtfo_dir.exists():
        log.warning("GTFOBins source missing: %s", gtfo_dir)
        return []
    results = []
    for entry_path in sorted(gtfo_dir.iterdir()):
        if not entry_path.is_file():
            continue
        name = entry_path.name
        try:
            raw = entry_path.read_text(encoding='utf-8', errors='replace')
            # YAML document: starts with --- ends with --- or ...
            m = re.match(r'^---\n(.*?)(?:\n---|\n\.\.\.)\s*$', raw, re.DOTALL)
            if not m:
                # Try entire file as YAML
                data = yaml.safe_load(raw) or {}
            else:
                data = yaml.safe_load(m.group(1)) or {}
            body_html = _gtfobins_entry_html(name, data)
            if not body_html.strip():
                continue
            page_path = name.lower()
            funcs = data.get('functions') or {}
            func_tags = list(funcs.keys())
            # Collect contexts (sudo, suid, capabilities, unprivileged) from function entries
            ctx_tags = set()
            for entries in funcs.values():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if isinstance(entry, dict):
                        ctx_tags.update((entry.get('contexts') or {}).keys())
            # Encode as func:X and ctx:Y to distinguish in the index
            all_tags = [f'func:{t}' for t in func_tags] + [f'ctx:{c}' for c in sorted(ctx_tags)]
            r = _save_page("gtfobins", "GTFOBins", page_path, name, body_html, all_tags)
            results.append(r)
        except Exception as e:
            log.debug("GTFOBins skip %s: %s", name, e)
    return results

# ---------------------------------------------------------------------------
# LOLBAS processor (YAML files with .yml extension)
# ---------------------------------------------------------------------------
def _lolbas_entry_html(data: dict) -> str:
    name = data.get('Name','')
    desc = data.get('Description','')
    cmds = data.get('Commands') or []
    parts = [f'<h1>{html_lib.escape(name)}</h1>']
    if desc:
        parts.append(f'<p>{html_lib.escape(desc)}</p>')

    # Group by category
    by_cat = {}
    for cmd in cmds:
        if not isinstance(cmd, dict):
            continue
        cat = cmd.get('Category','Other')
        by_cat.setdefault(cat, []).append(cmd)

    for cat, cat_cmds in sorted(by_cat.items()):
        parts.append(f'<h2>{html_lib.escape(cat)}</h2>')
        for cmd in cat_cmds:
            usecase = cmd.get('Usecase','')
            command  = cmd.get('Command','')
            mitre    = cmd.get('MitreID','')
            priv     = cmd.get('Privileges','')
            cdesc    = cmd.get('Description','')
            if usecase:
                parts.append(f'<p>{html_lib.escape(str(usecase))}</p>')
            if command:
                parts.append(f'<pre><code class="language-powershell">{html_lib.escape(str(command))}</code></pre>')
            meta = []
            if cdesc: meta.append(html_lib.escape(str(cdesc)))
            if mitre:  meta.append(f'<strong>MITRE:</strong> {html_lib.escape(str(mitre))}')
            if priv:   meta.append(f'<strong>Privileges:</strong> {html_lib.escape(str(priv))}')
            if meta:
                parts.append('<p>' + ' &mdash; '.join(meta) + '</p>')
    return '\n'.join(parts)

def process_lolbas():
    lolbas_root = SOURCES / "lolbas" / "yml"
    if not lolbas_root.exists():
        log.warning("LOLBAS source missing: %s", lolbas_root)
        return []
    results = []
    for yml_file in sorted(lolbas_root.rglob("*.yml")):
        try:
            data = yaml.safe_load(yml_file.read_text(encoding='utf-8', errors='replace'))
            if not isinstance(data, dict):
                continue
            name = data.get('Name','')
            if not name:
                continue
            body_html = _lolbas_entry_html(data)
            if not body_html.strip():
                continue
            # Slugify: Certutil.exe → certutil
            slug = re.sub(r'\.[^.]+$','', name.lower()).replace(' ','-')
            cmds = data.get('Commands') or []
            tags = list(dict.fromkeys(
                c.get('Category','') for c in cmds
                if isinstance(c, dict) and c.get('Category')
            ))
            r = _save_page("lolbas", "LOLBAS", slug, name, body_html, tags)
            results.append(r)
        except Exception as e:
            log.debug("LOLBAS skip %s: %s", yml_file, e)
    return results

# ---------------------------------------------------------------------------
# Markdown task collection (existing sources + msfvenom)
# ---------------------------------------------------------------------------
def collect_tasks() -> list[tuple]:
    tasks = []
    for src in SOURCES_DEF:
        sid    = src["id"]
        label  = src["label"]
        root   = src["root"]
        skip_d = src["skip_dirs"]
        skip_f = src["skip_files"]

        if not root.exists():
            log.warning("Source missing: %s", root)
            continue

        if src["summary"]:
            items = parse_summary(src["summary"], root)
            for item in items:
                if item["path"].name in skip_f:
                    continue
                rel = item["path"].relative_to(root)
                page_path = str(rel.with_suffix('')).replace('\\','/').replace(' ','-')
                page_path = re.sub(r'/README$','',page_path)
                tasks.append((sid, label, item["path"], root, page_path))
        elif src.get("readme_only"):
            # For PATT-style repos: one README.md per top-level subdir = one page
            for subdir in sorted(root.iterdir()):
                if not subdir.is_dir():
                    continue
                if subdir.name in skip_d or subdir.name.startswith('_') or subdir.name.startswith('.'):
                    continue
                readme = subdir / "README.md"
                if readme.exists():
                    page_path = str(subdir.relative_to(root)).replace('\\','/').replace(' ','-')
                    tasks.append((sid, label, readme, root, page_path))
        else:
            for md in sorted(root.rglob("*.md")):
                if any(d in md.parts for d in skip_d):
                    continue
                if md.name in skip_f:
                    continue
                rel = md.relative_to(root)
                page_path = str(rel.with_suffix('')).replace('\\','/').replace(' ','-')
                page_path = re.sub(r'/README$','',page_path)
                tasks.append((sid, label, md, root, page_path))

    seen = set()
    unique = []
    for t in tasks:
        key = (t[0], t[4])
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    tasks = collect_tasks()
    log.info("Processing %d markdown files + GTFOBins + LOLBAS…", len(tasks))

    import shutil
    if PROCESSED.exists():
        shutil.rmtree(PROCESSED)
    PROCESSED.mkdir(parents=True)

    workers = min(cpu_count(), 8)
    with Pool(workers) as pool:
        md_results = pool.map(process_file, tasks)

    entries = [r for r in md_results if r is not None]

    # GTFOBins and LOLBAS are single-process (fast enough)
    log.info("Processing GTFOBins…")
    entries += [r for r in process_gtfobins() if r]
    log.info("Processing LOLBAS…")
    entries += [r for r in process_lolbas() if r]

    for i, e in enumerate(entries):
        e["id"] = i

    INDEX_PATH.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')

    # Pre-generate nav JSON for all sources so Railway (no sources/ dir) can serve them
    import sys
    sys.path.insert(0, str(ROOT))
    try:
        from app import _get_nav, SOURCE_META
        NAV_OUT = ROOT / "content" / "nav"
        NAV_OUT.mkdir(parents=True, exist_ok=True)
        for source_id in SOURCE_META:
            try:
                nav = _get_nav(source_id)
                (NAV_OUT / f"{source_id}.json").write_text(
                    json.dumps(nav, ensure_ascii=False), encoding='utf-8')
            except Exception as e:
                log.warning("Nav gen failed for %s: %s", source_id, e)
        log.info("Nav JSON pre-generated for %d sources", len(SOURCE_META))
    except Exception as e:
        log.warning("Nav pre-generation skipped: %s", e)

    from collections import Counter
    counts = Counter(e["source"] for e in entries)
    log.info("Done in %.1fs — %d pages indexed:", time.time()-t0, len(entries))
    for src, n in sorted(counts.items()):
        log.info("  %-25s %d", src, n)

if __name__ == "__main__":
    main()
