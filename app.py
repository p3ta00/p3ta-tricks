#!/usr/bin/env python3
"""p3ta-tricks Flask app — unified offline pentest reference."""
import json, re, os, shutil, yaml
from pathlib import Path
from flask import Flask, render_template, request, jsonify, abort, send_from_directory, Response, stream_with_context

ROOT          = Path(__file__).parent
PROCESSED     = ROOT / "content" / "processed"
INDEX         = ROOT / "static" / "search_index.json"
SOURCES       = ROOT / "sources"
NAV_CACHE_DIR = ROOT / "content" / "nav"

# Offline mode — set OFFLINE_MODE=1 and TOOLS_DIR=/path/to/tools
OFFLINE_MODE = os.environ.get("OFFLINE_MODE", os.environ.get("OFFLINE_MODE", "0")) == "1"
TOOLS_DIR    = Path(os.environ.get("TOOLS_DIR", ROOT.parent / "p3ta-tricks-offline" / "tools"))
BINARIES_DIR = ROOT / "binaries"  # compiled binaries served on online mode too
SITE_URL     = os.environ.get("SITE_URL", "https://p3ta-tricks.com")

# GitHub URL prefix → local tool directory name (for badge injection)
TOOL_MAP = {
    # ── Windows Privilege Escalation ──────────────────────────────────────────
    "BeichenDream/GodPotato":                    "GodPotato",
    "itm4n/PrintSpoofer":                        "PrintSpoofer",
    "itm4n/PrivescCheck":                        "PrivescCheck",
    "GhostPack/Seatbelt":                        "Seatbelt",
    "rasta-mouse/Watson":                        "Watson",
    "carlospolop/PEASS-ng":                      "PEASS-ng",
    "peass-ng/PEASS-ng":                         "PEASS-ng",
    "carlospolop/privilege-escalation-awesome-scripts-suite": "PEASS-ng",
    "ohpe/juicy-potato":                         "juicy-potato",
    "antonioCoco/RoguePotato":                   "RoguePotato",
    "CCob/SweetPotato":                          "SweetPotato",
    "GhostPack/SharpUp":                         "SharpUp",
    "gtworek/Priv2Admin":                        "Priv2Admin",
    "SecWiki/windows-kernel-exploits":           "windows-kernel-exploits",
    # ── GhostPack / C# Tools ──────────────────────────────────────────────────
    "GhostPack/Rubeus":                          "Rubeus",
    "GhostPack/Certify":                         "Certify",
    "GhostPack/SharpDPAPI":                      "SharpDPAPI",
    "GhostPack/SafetyKatz":                      "SafetyKatz",
    "Flangvik/SharpCollection":                  "SharpCollection",
    "tevora-threat/SharpView":                   "SharpView",
    "0xthirteen/SharpMove":                      "SharpMove",
    # ── ADCS / Certificate Attacks ────────────────────────────────────────────
    "ly4k/Certipy":                              "Certipy",
    "AlmondOffSec/PassTheCert":                  "PassTheCert",
    "jamarir/Invoke-PassTheCert":                "PassTheCert",
    "bats3c/ADCSPwn":                            "ADCSPwn",
    # ── Kerberos Attacks ──────────────────────────────────────────────────────
    "dirkjanm/krbrelayx":                        "krbrelayx",
    "dirkjanm/PKINITtools":                      "PKINITtools",
    "ShutdownRepo/targetedKerberoast":           "targetedKerberoast",
    "ropnop/kerbrute":                           "kerbrute",
    "gentilkiwi/kekeo":                          "kekeo",
    "TarlogicSecurity/tickey":                   "tickey",
    "SecuraBV/Timeroast":                        "Timeroast",
    # ── Coercion & NTLM Relay ─────────────────────────────────────────────────
    "topotam/PetitPotam":                        "PetitPotam",
    "p0dalirius/Coercer":                        "Coercer",
    "Wh04m1001/DFSCoerce":                       "DFSCoerce",
    "ShutdownRepo/ShadowCoerce":                 "ShadowCoerce",
    "lgandx/Responder":                          "Responder",
    "dirkjanm/mitm6":                            "mitm6",
    "Kevin-Robertson/Inveigh":                   "Inveigh",
    # ── Shadow Credentials ────────────────────────────────────────────────────
    "eladshamir/Whisker":                        "Whisker",
    "ShutdownRepo/pywhisker":                    "pywhisker",
    # ── AD Enumeration & Manipulation ─────────────────────────────────────────
    "dirkjanm/BloodHound.py":                    "BloodHound.py",
    "CravateRouge/bloodyAD":                     "bloodyAD",
    "PowerShellMafia/PowerSploit":               "PowerSploit",
    "FuzzySecurity/StandIn":                     "StandIn",
    "dirkjanm/ldapdomaindump":                   "ldapdomaindump",
    "dirkjanm/ROADtools":                        "ROADtools",
    "Kevin-Robertson/Powermad":                  "Powermad",
    "franc-pentest/ldeep":                       "ldeep",
    "SnaffCon/Snaffler":                         "Snaffler",
    "EmpireProject/Empire":                      "Empire",
    # ── gMSA Attacks ──────────────────────────────────────────────────────────
    "Semperis/GoldenGMSA":                       "GoldenGMSA",
    "felixbillieres/pyGoldenGMSA":               "pyGoldenGMSA",
    # ── SCCM / MECM ───────────────────────────────────────────────────────────
    "subat0mik/Misconfiguration-Manager":        "Misconfiguration-Manager",
    "Mayyhem/SharpSCCM":                         "SharpSCCM",
    "garrettfoster13/sccmhunter":                "sccmhunter",
    # ── LSASS Dumping & Credential Extraction ────────────────────────────────
    "Hackndo/lsassy":                            "lsassy",
    "fortra/nanodump":                           "nanodump",
    "AlessandroZ/LaZagne":                       "LaZagne",
    "login-securite/DonPAPI":                    "DonPAPI",
    "skelsec/pypykatz":                          "pypykatz",
    "lgandx/PCredz":                             "PCredz",
    # ── Credentials / Mimikatz ────────────────────────────────────────────────
    "gentilkiwi/mimikatz":                       "mimikatz-tool",
    # ── MSSQL Attacks ─────────────────────────────────────────────────────────
    "NetSPI/PowerUpSQL":                         "PowerUpSQL",
    "ScorpionesLabs/MSSqlPwner":                 "MSSqlPwner",
    # ── PowerShell Post-Exploitation ─────────────────────────────────────────
    "samratashok/nishang":                       "nishang",
    # ── Tunneling & Pivoting ──────────────────────────────────────────────────
    "jpillora/chisel":                           "chisel",
    "Fahrj/reverse-ssh":                         "reverse-ssh",
    # ── Linux Enumeration & Exploitation ─────────────────────────────────────
    "DominicBreuker/pspy":                       "pspy",
    "diego-treitos/linux-smart-enumeration":     "linux-smart-enumeration",
    "nongiach/sudo_inject":                      "sudo_inject",
    # ── Certificate Forgery ───────────────────────────────────────────────────
    "GhostPack/ForgeCert":                       "ForgeCert",
    # ── CVE PoCs ──────────────────────────────────────────────────────────────
    "cube0x0/CVE-2021-1675":                     "CVE-2021-1675",
    "BreenmMachine/RottenPotatoNG":              "RottenPotatoNG",
    "breenmachine/RottenPotatoNG":               "RottenPotatoNG",
    # ── Network / MITM ────────────────────────────────────────────────────────
    "SpiderLabs/Responder":                      "Responder",
    "spiderlabs/Responder":                      "Responder",
    "bettercap/bettercap":                       "bettercap",
    # ── Impacket aliases (standard kali — link to wiki source) ───────────────
    "SecureAuthCorp/impacket":                   "impacket-src",
    "fortra/impacket":                           "impacket-src",
    # ── NetExec ───────────────────────────────────────────────────────────────
    "Pennyw0rth/NetExec":                        "NetExec",
    "Pennyw0rth/NetExec-Wiki":                   "NetExec",
    # ── .NET Reverse Engineering ──────────────────────────────────────────────
    "dnspy/dnspy":                               "dnspy",
    # ── Java Deserialization ──────────────────────────────────────────────────
    "frohoff/ysoserial":                         "ysoserial-java",
    # ── Web Exploitation ──────────────────────────────────────────────────────
    "pwntester/ysoserial.net":                   "ysoserial.net",
    "epinna/tplmap":                             "tplmap",
    "tarunkant/Gopherus":                        "Gopherus",
    "ticarpi/jwt_tool":                          "jwt_tool",
    # ── Azure / Cloud ─────────────────────────────────────────────────────────
    "NetSPI/MicroBurst":                         "MicroBurst",
    "RhinoSecurityLabs/pacu":                    "pacu",
    # ── BloodHound ────────────────────────────────────────────────────────────
    "BloodHoundAD/BloodHound":                   "BloodHound.py",
    # ── Misc ──────────────────────────────────────────────────────────────────
    "Hackndo/pyGPOAbuse":                        "pyGPOAbuse",
    "n00py/LAPSDumper":                          "LAPSDumper",
    "layer8secure/SilentHound":                  "SilentHound",
    "t3l3machus/Villain":                        "Villain",
    "sensepost/objection":                       "objection",
    # ── Web Recon / SSRF / Fuzzing ────────────────────────────────────────────
    "assetnote/blind-ssrf-chains":              "blind-ssrf-chains",
    "s0md3v/Arjun":                             "Arjun",
    # ── VoIP ─────────────────────────────────────────────────────────────────
    "Pepelux/sippts":                           "sippts",
    # ── Java RMI ─────────────────────────────────────────────────────────────
    "qtc-de/remote-method-guesser":             "remote-method-guesser",
}

app = Flask(__name__)


@app.context_processor
def inject_globals():
    """Inject globals into every template."""
    base = {"site_url": SITE_URL}
    if not OFFLINE_MODE:
        base.update({"offline_mode": False, "offline_config_json": "null"})
        return base
    available = {name: True for name in set(TOOL_MAP.values())
                 if (TOOLS_DIR / name).exists()}
    cfg = {"offline": True, "tools": available, "tool_map": TOOL_MAP}
    base.update({"offline_mode": True, "offline_config_json": json.dumps(cfg)})
    return base

SOURCE_META = {
    "bloodhound":      {"label": "BloodHound",          "color": "var(--red)",     "icon": "🩸"},
    "hacker-recipes":  {"label": "The Hacker Recipes", "color": "var(--cyan)",    "icon": "🍳"},
    "hacktricks":      {"label": "HackTricks",          "color": "var(--red)",     "icon": "🤖"},
    "hacktricks-cloud":{"label": "HackTricks Cloud",    "color": "var(--blue)",    "icon": "☁️"},
    "netexec":         {"label": "NetExec Wiki",         "color": "var(--green)",   "icon": "🔧"},
    "gtfobins":        {"label": "GTFOBins",             "color": "var(--orange)",  "icon": "🐚"},
    "lolbas":          {"label": "LOLBAS",               "color": "var(--yellow)",  "icon": "🪟"},
    "wadcoms":         {"label": "WADComs",              "color": "var(--blue)",    "icon": "🏴"},
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
    "enum":            {"label": "Enumeration",           "color": "var(--green)",   "icon": "🔍"},
    "revshells":       {"label": "Reverse Shells",        "color": "var(--orange)",  "icon": "🐚"},
    "bug-bounty":      {"label": "Bug Bounty",            "color": "var(--yellow)",  "icon": "🐛"},
    "active-directory": {"label": "Active Directory",           "color": "var(--green)",   "icon": "🎓"},
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
    "enum": {
        "root":    SOURCES / "enum",
        "summary": SOURCES / "enum" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    "revshells": {
        "root":    SOURCES / "revshells",
        "summary": SOURCES / "revshells" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
    "bug-bounty": {
        "root":    SOURCES / "bug-bounty",
        "summary": SOURCES / "bug-bounty" / "SUMMARY.md",
        "skip_dirs": {"Bypass", "Checklist", "CVEs", "Misc", "Reconnaissance", "Technologies"},
        "skip_files": {"README.md"},
        "readme_only": False,
    },
    "active-directory": {
        "root":    SOURCES / "active-directory",
        "summary": SOURCES / "active-directory" / "SUMMARY.md",
        "skip_dirs": set(),
        "skip_files": {"SUMMARY.md"},
    },
}

_EMOJI_RE   = re.compile(r'[\U0001F000-\U0001FFFF‍ -⟿☀-⟿︀-﻿]+\s*')
_LINK_RE    = re.compile(r'^(\s*)[-*]\s+\[([^\]]+)\]\(([^)]+\.md(?:#[^)]*)?)\)')
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
            safe_hyp = safe.replace(" ", "-")
            candidates = list((PROCESSED / source).glob(f"{safe_hyp}.json"))
        if not candidates:
            candidates = list(PROCESSED.rglob(f"{safe}.json"))
        if not candidates:
            candidates = list(PROCESSED.rglob(f"{safe.replace(' ', '-')}.json"))
        if not candidates:
            return None
        try:
            data = json.loads(candidates[0].read_text(encoding="utf-8"))
            if 'html' in data:
                data['html'] = re.sub(r'\{\{#[^}]*\}\}', '', data['html'])
            _page_cache[key] = data
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
    anchor = ''
    if '#' in rel:
        rel, frag = rel.split('#', 1)
        anchor = '#' + frag
    try:
        abs_path = (summary_path.parent / rel).resolve()
        rel_to_root = abs_path.relative_to(root)
        page_path = str(rel_to_root.with_suffix('')).replace('\\', '/').replace(' ', '-')
        page_path = re.sub(r'/README$', '', page_path)
        return f'/page/{source_id}/{page_path}{anchor}'
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

    # If sources/ dir is unavailable (e.g. Railway), serve pre-built nav JSON
    pre_built = NAV_CACHE_DIR / f"{source_id}.json"
    if not cfg['root'].exists() and pre_built.exists():
        tree = json.loads(pre_built.read_text(encoding='utf-8'))
        _nav_cache[source_id] = tree
        return tree

    if cfg['summary'] and cfg['summary'].exists():
        flat = _parse_flat_from_summary(source_id, cfg)
    else:
        flat = _parse_flat_from_dir(source_id, cfg)

    tree = _flat_to_tree(flat)

    if source_id == "bloodhound":
        tree.insert(0, {"type": "link", "title": "BloodHound Search", "url": "/source/bloodhound", "items": []})

    # If nav has exactly one section whose title is generic ("CONTENTS") or matches
    # the source label, flatten items to top-level links to avoid redundant header.
    if (len(tree) == 1 and
            tree[0].get('type') == 'section' and
            tree[0].get('title', '').upper() in (
                'CONTENTS',
                SOURCE_META.get(source_id, {}).get('label', '').upper(),
                source_id.upper())):
        tree = [{'type': 'link', 'title': item['title'], 'url': item['url'],
                 'children': item.get('children', [])}
                for item in tree[0].get('items', [])]

    _nav_cache[source_id] = tree
    return tree


# ---------------------------------------------------------------------------
# RevShells — load from authoritative data.js export
# ---------------------------------------------------------------------------
_revshells_cache = None

_RS_TYPE_TO_TAB = {
    'ReverseShell': 'reverse',
    'BindShell':    'bind',
    'MSFVenom':     'msfvenom',
    'HoaxShell':    'hoax',
    'Assembled':    'assembled',
}

def _parse_revshells_app():
    global _revshells_cache
    if _revshells_cache is not None:
        return _revshells_cache
    data_path = SOURCES / "revshells" / "shells_data.json"
    if not data_path.exists():
        _revshells_cache = {'shells': [], 'listeners': [], 'shell_types': []}
        return _revshells_cache
    raw = json.loads(data_path.read_text(encoding='utf-8'))
    shells = []
    for uid, entry in enumerate(raw.get('allShells', [])):
        meta    = entry.get('meta', [])
        tab     = next((_RS_TYPE_TO_TAB[m] for m in meta if m in _RS_TYPE_TO_TAB), 'reverse')
        os_tags = [m for m in meta if m in ('linux', 'mac', 'windows')]
        shells.append({
            'id':      uid,
            'name':    entry.get('name', ''),
            'command': entry.get('command', ''),
            'tab':     tab,
            'os':      os_tags,
        })
    result = {
        'shells':      shells,
        'listeners':   raw.get('listenerCommands', []),
        'shell_types': raw.get('shells', []),
    }
    _revshells_cache = result
    return result


# ---------------------------------------------------------------------------
# WADComs parser
# ---------------------------------------------------------------------------
_wadcoms_cache = None

def _load_wadcoms() -> list:
    global _wadcoms_cache
    if _wadcoms_cache is not None:
        return _wadcoms_cache
    wad_dir = SOURCES / "wadcoms" / "_wadcoms"
    entries = []
    if not wad_dir.exists():
        return entries
    _FM_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)
    for md_file in sorted(wad_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="ignore")
        m = _FM_RE.search(text)
        if not m:
            continue
        try:
            data = yaml.safe_load(m.group(1)) or {}
        except Exception:
            continue
        slug = md_file.stem
        # Normalize command: replace common literal IPs/users with site variables
        cmd = (data.get("command") or "").strip()
        cmd = re.sub(r'\b10\.10\.10\.1\b', '<ip>', cmd)
        cmd = re.sub(r'\b192\.168\.\d+\.\d+\b', '<ip>', cmd)
        cmd = re.sub(r'\bjohn\b', '<username>', cmd)
        cmd = re.sub(r'\bpassword123\b', '<password>', cmd)
        cmd = re.sub(r'\bdomain\.local\b', '<domain>', cmd)
        entries.append({
            "slug":         slug,
            "title":        slug.replace("-", " ").replace("_", " "),
            "description":  (data.get("description") or "").strip(),
            "command":      cmd,
            "have":         data.get("items") or [],
            "os":           data.get("OS") or [],
            "attack_types": data.get("attack_types") or [],
            "services":     data.get("services") or [],
            "references":   data.get("references") or [],
        })
    _wadcoms_cache = entries
    return entries


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
        if meta.get("offline_only") and not OFFLINE_MODE:
            continue
        sources.append({**meta, "id": sid, "count": counts.get(sid, 0)})
    return render_template("index.html", sources=sources, total=len(idx))


@app.route("/search")
def search():
    q       = request.args.get("q", "").strip()
    source  = request.args.get("source", "")
    fmt     = request.args.get("format", "")
    results = _search(q)
    if not OFFLINE_MODE:
        _hidden = {sid for sid, m in SOURCE_META.items() if m.get("offline_only")}
        results = [r for r in results if r.get("source") not in _hidden]
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
    if SOURCE_META[source_id].get("offline_only") and not OFFLINE_MODE:
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

    if source_id == "revshells":
        shell_types = _parse_revshells_app()
        return render_template("revshells_app.html", source_id=source_id, meta=meta,
                               shell_types=shell_types, source_meta=SOURCE_META)

    if source_id == "wadcoms":
        wadcoms_entries = _load_wadcoms()
        return render_template("wadcoms_source.html", source_id=source_id, meta=meta,
                               entries=wadcoms_entries, source_meta=SOURCE_META)

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


@app.route("/cyberchef/")
@app.route("/cyberchef/<path:sub>")
def cyberchef(sub=""):
    return render_template("cyberchef.html", source_meta=SOURCE_META)


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


# ---------------------------------------------------------------------------
# Compiled binaries — available in both online and offline modes
# ---------------------------------------------------------------------------

def _get_all_binaries() -> list[dict]:
    """Return sorted list of all downloadable compiled binaries."""
    binaries = []
    if not BINARIES_DIR.exists():
        return binaries
    for tool_dir in sorted(BINARIES_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        tool_name = tool_dir.name
        for f in sorted(tool_dir.iterdir()):
            if f.is_file():
                sz = f.stat().st_size
                binaries.append({
                    "tool": tool_name,
                    "name": f.name,
                    "path": f"{tool_name}/{f.name}",
                    "size": sz,
                    "size_str": f"{sz/1048576:.1f} MB" if sz > 1048576 else f"{sz/1024:.0f} KB",
                })
    return binaries


@app.route("/binaries/")
def binaries_index():
    binaries = _get_all_binaries()
    # Group by tool
    by_tool = {}
    for b in binaries:
        by_tool.setdefault(b["tool"], []).append(b)
    return render_template("binaries_index.html", by_tool=by_tool, total=len(binaries))


@app.route("/binaries/<tool_name>/<filename>")
def serve_binary(tool_name, filename):
    tool_path = BINARIES_DIR / tool_name
    if not tool_path.exists():
        abort(404)
    f = tool_path / filename
    if not f.exists() or not f.is_file():
        abort(404)
    return send_from_directory(str(tool_path), filename, as_attachment=True)


# ---------------------------------------------------------------------------
# Offline mode routes (/tools/)
# ---------------------------------------------------------------------------
@app.route("/api/offline-config")
def offline_config():
    if not OFFLINE_MODE:
        return jsonify({"offline": False})
    available = {name: True for name in TOOL_MAP.values()
                 if (TOOLS_DIR / name).exists()}
    return jsonify({"offline": True, "tools": available, "tool_map": TOOL_MAP})


@app.route("/tools/")
def tools_index():
    if not OFFLINE_MODE:
        abort(404)
    tools = sorted(
        [d.name for d in TOOLS_DIR.iterdir() if d.is_dir()] if TOOLS_DIR.exists() else []
    )
    return render_template("tools_index.html", tools=tools)


@app.route("/tools/<tool_name>/")
@app.route("/tools/<tool_name>/<path:filepath>")
def serve_tool_file(tool_name, filepath=""):
    if not OFFLINE_MODE:
        abort(404)
    tool_path = TOOLS_DIR / tool_name
    if not tool_path.exists():
        abort(404)
    target = tool_path / filepath if filepath else tool_path
    if not target.exists():
        abort(404)
    if target.is_file():
        return send_from_directory(str(target.parent), target.name)
    # Directory listing — dirs first, then files, each alphabetical
    items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    entries = [{"name": p.name, "is_dir": p.is_dir(),
                "size": p.stat().st_size if p.is_file() else None} for p in items]
    parent = str(Path(filepath).parent) if filepath and '/' in filepath else ""

    # Pre-built binaries: releases/ subdir (Go/compiled tools) + SharpCollection (GhostPack)
    sharp_prebuilt = []
    has_requirements = False
    if not filepath:
        # releases/ directory binaries (kerbrute, chisel, pspy, reverse-ssh, bettercap, etc.)
        releases_dir = tool_path / "releases"
        if releases_dir.exists():
            for f in sorted(releases_dir.iterdir()):
                if f.is_file():
                    sharp_prebuilt.append({
                        "tier": "pre-built",
                        "name": f.name,
                        "path": f"{tool_name}/releases/{f.name}",
                        "size": f.stat().st_size,
                    })

        # SharpCollection (GhostPack) binaries
        sc_root = TOOLS_DIR / "SharpCollection"
        if sc_root.exists():
            tiers = ["NetFramework_4.7_Any", "NetFramework_4.7_x64",
                     "NetFramework_4.0_Any", "NetFramework_4.0_x64"]
            candidates = [tool_name, tool_name.replace("-", ""), tool_name.replace("_", "")]
            seen = set()
            for tier in tiers:
                for cand in candidates:
                    binary = sc_root / tier / f"{cand}.exe"
                    if binary.exists() and cand not in seen:
                        seen.add(cand)
                        sharp_prebuilt.append({
                            "tier": tier,
                            "name": binary.name,
                            "path": f"SharpCollection/{tier}/{binary.name}",
                            "size": binary.stat().st_size,
                        })

        # Script tool detection — check root and one level of subdirs
        _req_files = ("requirements.txt", "setup.py", "pyproject.toml", "setup.cfg")
        has_pip_install = (
            any((tool_path / f).exists() for f in _req_files) or
            any(p.exists() for f in _req_files for p in tool_path.glob(f"*/{f}"))
        )
        is_powershell = bool(
            list(tool_path.glob("*.ps1")) or list(tool_path.glob("*.psm1")) or
            list(tool_path.glob("*/*.ps1")) or list(tool_path.glob("*/*.psm1"))
        )
        is_python_script = (
            not has_pip_install and (
                bool(list(tool_path.glob("*.py"))) or
                bool(list(tool_path.glob("*/*.py")))
            )
        )
        has_requirements = has_pip_install or is_python_script or is_powershell

    return render_template("tool_dir.html", tool_name=tool_name,
                           filepath=filepath, parent=parent, entries=entries,
                           sharp_prebuilt=sharp_prebuilt,
                           has_requirements=has_requirements,
                           has_pip_install=has_pip_install if not filepath else False,
                           is_powershell=is_powershell if not filepath else False,
                           is_python_script=is_python_script if not filepath else False)


@app.route("/tools/<tool_name>/zip")
def download_tool_zip(tool_name):
    """Stream the entire tool directory as a zip archive."""
    import zipfile, io
    if not OFFLINE_MODE:
        abort(404)
    tool_path = TOOLS_DIR / tool_name
    if not tool_path.exists():
        abort(404)

    def _stream_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for f in sorted(tool_path.rglob("*")):
                if f.is_file() and ".git" not in f.parts:
                    zf.write(f, f.relative_to(tool_path.parent))
        buf.seek(0)
        while True:
            chunk = buf.read(65536)
            if not chunk:
                break
            yield chunk

    return Response(
        stream_with_context(_stream_zip()),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={tool_name}.zip"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
