#!/usr/bin/env python3
"""Rebuild generated resources that are not ordinary Markdown wiki clones.

Inputs (all under sources/): LOLBAS YAML, WADComs front matter, Sliver docs,
Adaptix GitBook export, and the official Exploit-DB CSV/corpus. Also records a
machine-readable source lock so every generated snapshot has provenance.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
PROCESSED = ROOT / "content" / "processed"
NAV = ROOT / "content" / "nav"
LOCK = ROOT / "content" / "source-lock.json"

REPOS = {
    "hacktricks": ("hacktricks", "https://github.com/HackTricks-wiki/hacktricks.git"),
    "hacktricks-cloud": ("hacktricks-cloud", "https://github.com/HackTricks-wiki/hacktricks-cloud.git"),
    "hacker-recipes": ("hacker-recipes", "https://github.com/ShutdownRepo/The-Hacker-Recipes.git"),
    "netexec": ("netexec-wiki", "https://github.com/Pennyw0rth/NetExec-Wiki.git"),
    "patt": ("payloadsallthethings", "https://github.com/swisskyrepo/PayloadsAllTheThings.git"),
    "internal-att": ("internalallthethings", "https://github.com/swisskyrepo/InternalAllTheThings.git"),
    "hardware-att": ("hardwareallthethings", "https://github.com/swisskyrepo/HardwareAllTheThings.git"),
    "bloodyad": ("bloodyad-wiki", "https://github.com/CravateRouge/bloodyAD.wiki.git"),
    "certipy": ("certipy-wiki", "https://github.com/ly4k/Certipy.wiki.git"),
    "ligolo-ng": ("ligolo-ng-wiki", "https://github.com/nicocha30/ligolo-ng.wiki.git"),
    "goexec": ("goexec", "https://github.com/FalconOpsLLC/goexec.git"),
    "lolbas": ("lolbas", "https://github.com/LOLBAS-Project/LOLBAS.git"),
    "wadcoms": ("wadcoms", "https://github.com/WADComs/WADComs.github.io.git"),
    "sliver": ("sliver", "https://github.com/BishopFox/sliver.git"),
    "exploitdb": ("exploitdb-new", "https://gitlab.com/exploit-database/exploitdb.git"),
}


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def repo_meta(path: Path, url: str) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()
    return {
        "url": url,
        "branch": git("branch", "--show-current"),
        "commit": git("rev-parse", "HEAD"),
        "commit_time": git("show", "-s", "--format=%cI", "HEAD"),
    }


def write_json(path: Path, value, *, pretty=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2 if pretty else None), encoding="utf-8")


def rebuild_lolbas() -> int:
    src = SOURCES / "lolbas" / "yml"
    out = PROCESSED / "lolbas"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    pages = []
    used_slugs = set()
    for file in sorted(src.rglob("*.yml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        name = str(data.get("Name") or file.stem)
        # LOLBAS currently contains a binary and a script with the same stem.
        # Preserve the established route for the first and disambiguate later
        # collisions using the actual extension from Name.
        slug = file.stem.lower()
        if slug in used_slugs:
            extension = Path(name).suffix.lower().lstrip(".") or file.parent.name.lower()
            slug = f"{slug}-{extension}"
        if slug in used_slugs:
            raise RuntimeError(f"unresolved LOLBAS slug collision: {file}")
        used_slugs.add(slug)
        parts = [f"<h1>{esc(name)}</h1>", f"<p>{esc(data.get('Description'))}</p>"]
        paths = [x.get("Path") for x in data.get("Full_Path", []) if isinstance(x, dict) and x.get("Path")]
        if paths:
            parts.append("<h2>Paths</h2><ul>" + "".join(f"<li><code>{esc(x)}</code></li>" for x in paths) + "</ul>")
        commands = data.get("Commands") or []
        if commands:
            parts.append("<h2>Commands</h2>")
        tags = set()
        for cmd in commands:
            if not isinstance(cmd, dict):
                continue
            cat = str(cmd.get("Category") or "Command")
            tags.add(cat)
            parts.extend([
                f"<h3>{esc(cat)}</h3>",
                f"<p>{esc(cmd.get('Description'))}</p>",
                f"<p><em>Use case: {esc(cmd.get('Usecase'))}</em></p>",
                f"<p><em>Privileges: {esc(cmd.get('Privileges'))}</em></p>",
                f"<pre><code class=\"language-bash\">{esc(cmd.get('Command'))}</code></pre>",
            ])
        for section in ("Detection", "Resources", "Acknowledgement"):
            vals = data.get(section) or []
            if not vals:
                continue
            parts.append(f"<h2>{section}</h2><ul>")
            for item in vals:
                if isinstance(item, dict):
                    text = ": ".join(f"{k}: {v}" for k, v in item.items())
                else:
                    text = str(item)
                parts.append(f"<li>{esc(text)}</li>")
            parts.append("</ul>")
        page = {
            "title": name, "source": "lolbas", "source_label": "LOLBAS",
            "path": slug, "html": "\n".join(parts),
            "excerpt": str(data.get("Description") or "")[:500],
            "tags": sorted(tags),
        }
        write_json(out / f"{slug}.json", page)
        pages.append(page)
    return len(pages)


def rebuild_wadcoms() -> int:
    entries = []
    fm = re.compile(r"^---\s*\n(.*?)\n---", re.S)
    for file in sorted((SOURCES / "wadcoms" / "_wadcoms").glob("*.md")):
        text = file.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff\r\n ")
        match = fm.search(text)
        if not match:
            raise RuntimeError(f"WADComs page has no valid front matter: {file}")
        data = yaml.safe_load(match.group(1)) or {}
        command = str(data.get("command") or "").strip()
        command = re.sub(r"\b10\.10\.10\.1\b", "<ip>", command)
        command = re.sub(r"\b192\.168\.\d+\.\d+\b", "<ip>", command)
        command = re.sub(r"\bjohn\b", "<username>", command, flags=re.I)
        command = re.sub(r"\bpassword123\b", "<password>", command, flags=re.I)
        command = re.sub(r"\bdomain\.local\b", "<domain>", command, flags=re.I)
        entries.append({
            "slug": file.stem,
            "title": file.stem.replace("-", " ").replace("_", " "),
            "description": str(data.get("description") or "").strip(),
            "command": command,
            "have": data.get("items") or [], "os": data.get("OS") or [],
            "attack_types": data.get("attack_types") or [],
            "services": data.get("services") or [], "references": data.get("references") or [],
        })
    write_json(ROOT / "content" / "wadcoms_data.json", entries, pretty=True)
    return len(entries)


def prepare_sliver() -> int:
    src = SOURCES / "sliver" / "docs" / "sliver-docs"
    dest = SOURCES / "sliver-docs"
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for folder in ("pages/docs/md", "pages/tutorials/md"):
        for file in (src / folder).glob("*.md"):
            prefix = "Tutorial - " if "tutorials" in folder else ""
            shutil.copy2(file, dest / f"{prefix}{file.name}")
    shutil.copytree(src / "public" / "images", dest / "images")
    return len(list(dest.glob("*.md")))


def rebuild_exploitdb() -> int:
    src = SOURCES / "exploitdb-new"
    entries = []
    with (src / "files_exploits.csv").open(encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            codes = [x.strip() for x in (row.get("codes") or "").split(";") if x.strip()]
            entries.append({
                "id": int(row["id"]), "title": row["description"], "type": row["type"],
                "platform": row["platform"], "date": row["date_published"], "author": row["author"],
                "cve": [x for x in codes if x.upper().startswith("CVE-")],
                "tags": [x.strip() for x in (row.get("tags") or "").split(";") if x.strip()],
                "verified": row.get("verified") == "1", "path": row["file"],
            })
    entries.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    write_json(ROOT / "content" / "exploitdb_index.json", entries)
    return len(entries)


def main():
    counts = {
        "lolbas": rebuild_lolbas(),
        "wadcoms": rebuild_wadcoms(),
        "sliver": prepare_sliver(),
        "exploitdb": rebuild_exploitdb(),
    }
    locks = {}
    for sid, (directory, url) in REPOS.items():
        count = counts.get(sid)
        if count is None:
            count = len(list((PROCESSED / sid).glob("*.json")))
        locks[sid] = {**repo_meta(SOURCES / directory, url), "processed_count": count}
    adaptix_llms = SOURCES / "adaptix" / ".source.json"
    if adaptix_llms.exists():
        locks["adaptix"] = json.loads(adaptix_llms.read_text(encoding="utf-8"))
        locks["adaptix"]["processed_count"] = len(list((PROCESSED / "adaptix").glob("*.json")))
    church_meta = SOURCES / "churchofmalware" / ".source.json"
    if church_meta.exists():
        locks["churchofmalware"] = json.loads(church_meta.read_text(encoding="utf-8"))
    locks["generated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(LOCK, locks, pretty=True)
    print(json.dumps({"counts": counts, "lock": str(LOCK)}, indent=2))


if __name__ == "__main__":
    main()
