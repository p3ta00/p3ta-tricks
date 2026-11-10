#!/usr/bin/env python3
"""Rebuild content/processed JSON and search index for all main sources.

Usage:
    python3 scripts/rebuild_sources.py              # rebuild all sources
    python3 scripts/rebuild_sources.py netexec      # rebuild one source
    python3 scripts/rebuild_sources.py netexec hacktricks  # rebuild specific sources
"""
import json, re, shutil, sys
from pathlib import Path
import markdown as md_lib
from inject_copy_blocks import inject_copy_blocks
from inject_variable_tokens import inject_variable_tokens

ROOT      = Path(__file__).parent.parent
SOURCES   = ROOT / "sources"
PROCESSED = ROOT / "content" / "processed"
NAV_DIR   = ROOT / "content" / "nav"
INDEX     = ROOT / "static" / "search_index.json"

MD_EXTENSIONS = [
    "fenced_code", "tables", "toc", "attr_list", "admonition",
    "pymdownx.superfences", "pymdownx.highlight",
]

SOURCE_LABELS = {
    "netexec":          "NetExec Wiki",
    "hacktricks":       "HackTricks",
    "hacktricks-cloud": "HackTricks Cloud",
    "hacker-recipes":   "The Hacker Recipes",
    "hardware-att":     "HardwareAllTheThings",
    "internal-att":     "InternalAllTheThings",
    "patt":             "PayloadsAllTheThings",
    "bloodyad":         "bloodyAD",
    "certipy":          "Certipy",
    "ligolo-ng":        "Ligolo-ng",
    "sliver":           "Sliver C2",
    "impacket":         "Impacket",
    "gopacket":         "GoPacket",
    "rubeus":           "Rubeus",
    "mimikatz":         "Mimikatz",
    "bloodhound":       "BloodHound",
    "msfvenom":         "msfvenom",
    "goexec":           "goexec",
    "adaptix":          "Adaptix C2",
}

# Source configurations mirroring app.py _NAV_SOURCES
SOURCES_CFG = {
    "netexec": {
        "root":       SOURCES / "netexec-wiki",
        "summary":    SOURCES / "netexec-wiki" / "SUMMARY.md",
        "skip_files": {"SUMMARY.md", "logo-and-banner.md"},
        "skip_dirs":  set(),
    },
    "hacktricks": {
        "root":       SOURCES / "hacktricks" / "src",
        "summary":    SOURCES / "hacktricks" / "src" / "SUMMARY.md",
        "skip_files": {"SUMMARY.md", "LICENSE.md"},
        "skip_dirs":  set(),
    },
    "hacktricks-cloud": {
        "root":       SOURCES / "hacktricks-cloud" / "src",
        "summary":    SOURCES / "hacktricks-cloud" / "src" / "SUMMARY.md",
        "skip_files": {"SUMMARY.md", "LICENSE.md"},
        "skip_dirs":  set(),
    },
    "hacker-recipes": {
        "root":       SOURCES / "hacker-recipes" / "docs" / "src",
        "summary":    None,
        "skip_files": {"index.md", "variables.md", "template.md", "ads.md", "donate.md"},
        "skip_dirs":  {"assets", "contributing", ".vitepress"},
    },
    "hardware-att": {
        "root":       SOURCES / "hardwareallthethings" / "docs",
        "summary":    None,
        "skip_files": {"index.md"},
        "skip_dirs":  {"assets"},
    },
    "internal-att": {
        "root":       SOURCES / "internalallthethings" / "docs",
        "summary":    None,
        "skip_files": {"index.md"},
        "skip_dirs":  {"assets"},
    },
    "patt": {
        "root":       SOURCES / "payloadsallthethings",
        "summary":    None,
        "skip_files": {"README.md", "CONTRIBUTING.md", "DISCLAIMER.md"},
        "skip_dirs":  {"_LEARNING_AND_SOCIALS", "_template_vuln"},
        "readme_only": True,
    },
    "bloodyad": {
        "root":       SOURCES / "bloodyad-wiki",
        "summary":    None,
        "skip_files": {"_Footer.md"},
        "skip_dirs":  set(),
    },
    "certipy": {
        "root":       SOURCES / "certipy-wiki",
        "summary":    None,
        "skip_files": {"_Footer.md", "format.py"},
        "skip_dirs":  set(),
    },
    "ligolo-ng": {
        "root":       SOURCES / "ligolo-ng-wiki",
        "summary":    None,
        "skip_files": {"_Sidebar.md", "_Footer.md"},
        "skip_dirs":  set(),
    },
    "sliver": {
        "root":       SOURCES / "sliver-docs",
        "summary":    None,
        "skip_files": set(),
        "skip_dirs":  set(),
    },
    "impacket": {
        "root":       SOURCES / "impacket",
        "summary":    None,
        "skip_files": {"SUMMARY.md"},
        "skip_dirs":  set(),
    },
    "gopacket": {
        "root":       SOURCES / "gopacket-wiki",
        "summary":    None,
        "skip_files": {"Home.md"},
        "skip_dirs":  set(),
    },
    "rubeus": {
        "root":       SOURCES / "rubeus",
        "summary":    None,
        "skip_files": {"SUMMARY.md"},
        "skip_dirs":  set(),
    },
    "mimikatz": {
        "root":       SOURCES / "mimikatz",
        "summary":    None,
        "skip_files": {"SUMMARY.md"},
        "skip_dirs":  set(),
    },
    "bloodhound": {
        "root":       SOURCES / "bloodhound",
        "summary":    None,
        "skip_files": set(),
        "skip_dirs":  set(),
    },
    "msfvenom": {
        "root":       SOURCES / "msfvenom",
        "summary":    SOURCES / "msfvenom" / "SUMMARY.md",
        "skip_files": {"SUMMARY.md"},
        "skip_dirs":  set(),
    },
    "goexec": {
        "root":       SOURCES / "goexec",
        "summary":    None,
        "skip_files": set(),
        "skip_dirs":  {"cmd", "internal", "pkg"},
    },
    "adaptix": {
        "root":       SOURCES / "adaptix",
        "summary":    SOURCES / "adaptix" / "SUMMARY.md",
        "skip_files": {"README.md", "SUMMARY.md", "blogs.md", "changelog-and-updates.md"},
        "skip_dirs":  {"development", "changelog-and-updates"},
    },
}

_EMOJI_RE = re.compile(r'[\U0001F000-\U0001FFFF‍ -⟿︀-️﻿­]+\s*')
_LINK_RE  = re.compile(r'^\s*[-*]\s+\[([^\]]+)\]\(([^)]+\.md(?:#[^)]*)?)\)', re.M)
_GH_ALERT_RE = re.compile(
    r'^> \[!(NOTE|TIP|WARNING|CAUTION|DANGER|IMPORTANT|SUCCESS|INFO)\]([^\n]*)\n?((?:>[ \t]?[^\n]*\n?)*)',
    re.MULTILINE | re.IGNORECASE,
)


def _clean_title(t: str) -> str:
    return _EMOJI_RE.sub('', t).strip()


def _preprocess_alerts(text: str) -> str:
    def _replace(m):
        kind = m.group(1).lower()
        inline = m.group(2).strip()
        rest = re.sub(r'^> ?', '', m.group(3), flags=re.MULTILINE).strip()
        parts = [p for p in [inline, rest] if p]
        body = '\n'.join(parts)
        if not body:
            return f'!!! {kind}\n'
        indented = '\n'.join('    ' + line for line in body.splitlines())
        return f'!!! {kind}\n{indented}\n'
    return _GH_ALERT_RE.sub(_replace, text)


_HINT_KIND = {'info': 'info', 'warning': 'warning', 'danger': 'danger',
               'success': 'success', 'tip': 'tip'}

def _strip_gitbook_tags(text: str) -> str:
    # Strip YAML front matter (--- ... ---)
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)

    # Strip GitBook cloud image references (not resolvable without GitBook CDN)
    # Format: ![alt](<!-- gitbook-image:ID -->)
    text = re.sub(r'!\[[^\]]*\]\(<!-- gitbook-image:[^)]*-->\)', '', text)

    # {% hint style="..." %} ... {% endhint %} → admonition
    def _hint(m):
        kind = _HINT_KIND.get(m.group(1).lower(), 'info')
        body = m.group(2).strip()
        if not body:
            return f'!!! {kind}\n'
        indented = '\n'.join('    ' + line for line in body.splitlines())
        return f'!!! {kind}\n{indented}\n'
    text = re.sub(
        r'\{%\s*hint\s+style="([^"]+)"\s*%\}(.*?)\{%\s*endhint\s*%\}',
        _hint, text, flags=re.DOTALL | re.IGNORECASE,
    )

    # {% content-ref url="..." %} ... {% endcontent-ref %} → strip entirely
    text = re.sub(
        r'\{%\s*content-ref\s[^%]*%\}.*?\{%\s*endcontent-ref\s*%\}',
        '', text, flags=re.DOTALL | re.IGNORECASE,
    )

    # {% tabs %} / {% endtabs %} — strip wrapper, keep inner content
    text = re.sub(r'\{%\s*(?:end)?tabs\s*%\}', '', text, flags=re.IGNORECASE)

    # {% tab title="..." %} → markdown heading; {% endtab %} → strip
    text = re.sub(
        r'\{%\s*tab\s+title="([^"]+)"\s*%\}',
        lambda m: f'\n**{m.group(1)}**\n', text, flags=re.IGNORECASE,
    )
    text = re.sub(r'\{%\s*endtab\s*%\}', '', text, flags=re.IGNORECASE)

    # {% code title="..." %} / {% endcode %} — strip wrapper tags, keep code
    text = re.sub(r'\{%\s*code[^%]*%\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{%\s*endcode\s*%\}', '', text, flags=re.IGNORECASE)

    # {% file src="..." %} ... {% endfile %} → strip
    text = re.sub(
        r'\{%\s*file\s[^%]*%\}.*?\{%\s*endfile\s*%\}',
        '', text, flags=re.DOTALL | re.IGNORECASE,
    )

    # Any remaining {% ... %} tags — strip
    text = re.sub(r'\{%[^%]*%\}', '', text)

    return text


def _md_to_html(text: str) -> str:
    md = md_lib.Markdown(extensions=MD_EXTENSIONS)
    return md.convert(_preprocess_alerts(_strip_gitbook_tags(text)))


def _excerpt(html: str, n: int = 200) -> str:
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:n]


def _collect_from_summary(cfg: dict) -> list[tuple[str, str, Path]]:
    """Returns list of (title, page_path, file_path) from SUMMARY.md."""
    summary = cfg['summary']
    root    = cfg['root']
    skip    = cfg['skip_files']
    items   = []
    for line in summary.read_text(encoding='utf-8', errors='ignore').splitlines():
        m = re.match(r'^\s*[-*]\s+\[([^\]]+)\]\(([^)]+\.md)\)', line)
        if not m:
            continue
        title = _clean_title(m.group(1).strip())
        rel   = m.group(2).strip()
        if Path(rel).name in skip:
            continue
        fpath = (summary.parent / rel).resolve()
        if not fpath.exists():
            continue
        try:
            rel_to_root = fpath.relative_to(root)
        except ValueError:
            continue
        page_path = str(rel_to_root.with_suffix('')).replace('\\', '/').replace(' ', '-')
        page_path = re.sub(r'/README$', '', page_path)
        items.append((title, page_path, fpath))
    return items


def _collect_from_dir(cfg: dict) -> list[tuple[str, str, Path]]:
    """Returns list of (title, page_path, file_path) by walking the directory."""
    root       = cfg['root']
    skip_files = cfg['skip_files']
    skip_dirs  = cfg['skip_dirs']
    readme_only = cfg.get('readme_only', False)
    items = []

    if readme_only:
        for d in sorted(root.iterdir()):
            if not d.is_dir() or d.name in skip_dirs or d.name.startswith(('.', '_')):
                continue
            f = d / 'README.md'
            if not f.exists():
                continue
            page_path = d.name.replace(' ', '-')
            items.append((d.name, page_path, f))
        return items

    for f in sorted(root.rglob('*.md')):
        if f.name in skip_files:
            continue
        if any(part in skip_dirs for part in f.relative_to(root).parts):
            continue
        rel = f.relative_to(root)
        page_path = str(rel.with_suffix('')).replace('\\', '/').replace(' ', '-')
        page_path = re.sub(r'/README$', '', page_path)
        title = f.stem.replace('-', ' ').replace('_', ' ').title()
        items.append((title, page_path, f))
    return items


def build_source(source_id: str, cfg: dict) -> list[dict]:
    root = cfg['root']
    if not root.exists():
        print(f"  SKIP {source_id}: sources not found at {root}")
        return []

    label   = SOURCE_LABELS.get(source_id, source_id)
    out_dir = PROCESSED / source_id
    # A source rebuild is authoritative. Remove the previous generated tree so
    # pages deleted or renamed upstream do not survive forever as stale routes
    # and search results.
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if cfg.get('summary') and cfg['summary'].exists():
        items = _collect_from_summary(cfg)
    else:
        items = _collect_from_dir(cfg)

    # Sources where CLI placeholder injection is applied
    _VAR_SOURCES = {
        'netexec', 'bloodyad', 'certipy', 'hacker-recipes', 'internal-att',
        'hardware-att', 'patt', 'ligolo-ng', 'impacket', 'hacktricks',
        'hacktricks-cloud', 'goexec',
    }

    entries = []
    for title, page_path, fpath in items:
        text = fpath.read_text(encoding='utf-8', errors='ignore')
        # Strip gitbook include directives ({{#include ...}})
        text = re.sub(r'\{\{#[^}]*\}\}', '', text)
        if source_id in _VAR_SOURCES:
            text = inject_variable_tokens(text)
        html = inject_copy_blocks(_md_to_html(text))

        safe_key = page_path.replace('/', '__')
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
        out_file.write_text(json.dumps(page_data, ensure_ascii=False), encoding='utf-8')

        entries.append({
            "title":   title,
            "source":  source_id,
            "url":     f"/page/{source_id}/{page_path}",
            "path":    page_path,
            "excerpt": page_data["excerpt"],
            "tags":    page_data["tags"],
        })

    print(f"  [{source_id}] {len(entries)} pages rebuilt")
    return entries


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(SOURCES_CFG.keys())
    invalid = [t for t in targets if t not in SOURCES_CFG]
    if invalid:
        print(f"Unknown sources: {invalid}")
        print(f"Available: {list(SOURCES_CFG.keys())}")
        sys.exit(1)

    # Load existing index, strip entries for sources we're rebuilding
    existing = json.loads(INDEX.read_text(encoding='utf-8')) if INDEX.exists() else []
    existing = [e for e in existing if e.get('source') not in targets]

    new_entries = []
    for sid in targets:
        cfg = SOURCES_CFG[sid]
        entries = build_source(sid, cfg)
        new_entries.extend(entries)

    combined = existing + new_entries
    INDEX.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nDone. Index: {len(combined)} total ({len(new_entries)} rebuilt)")


if __name__ == "__main__":
    main()
