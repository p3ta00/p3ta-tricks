#!/usr/bin/env python3
"""
p3ta-tricks MCP maintenance server.
Gives Claude tools to check upstream sources for changes, pull updates,
rebuild the search index, and restart the Flask server.

Usage: python3 mcp_server.py
Add to ~/.claude/claude_desktop_config.json or .claude/settings.json.
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

ROOT = Path(__file__).parent.resolve()
SOURCES = ROOT / "sources"
BUILD_SCRIPT = ROOT / "scripts" / "build.py"

# All tracked sources with their upstream git repos
# "plain" sources (no .git) can't be auto-updated but are listed for awareness
SOURCE_REGISTRY = {
    "hacker-recipes":    {"dir": "hacker-recipes",    "git": True,  "label": "Hacker Recipes"},
    "hacktricks":        {"dir": "hacktricks",         "git": True,  "label": "HackTricks"},
    "hacktricks-cloud":  {"dir": "hacktricks-cloud",   "git": True,  "label": "HackTricks Cloud"},
    "netexec":           {"dir": "netexec-wiki",        "git": True,  "label": "NetExec"},
    "gtfobins":          {"dir": "gtfobins",            "git": True,  "label": "GTFOBins"},
    "lolbas":            {"dir": "lolbas",              "git": True,  "label": "LOLBAS"},
    "bloodyad":          {"dir": "bloodyad-wiki",       "git": True,  "label": "bloodyAD"},
    "certipy":           {"dir": "certipy-wiki",        "git": True,  "label": "Certipy"},
    "ligolo-ng":         {"dir": "ligolo-ng-wiki",      "git": True,  "label": "Ligolo-ng"},
    "patt":              {"dir": "payloadsallthethings", "git": True, "label": "PATT"},
    "hardware-att":      {"dir": "hardwareallthethings", "git": True, "label": "HardwareATT"},
    "internal-att":      {"dir": "internalallthethings", "git": True, "label": "InternalATT"},
    "goexec":            {"dir": "goexec",              "git": True,  "label": "GoExec"},
    "osai-research":     {"dir": "osai-research",       "git": True,  "label": "OSAI Research"},
    "sliver":            {"dir": "sliver-docs",         "git": False, "label": "Sliver (plain)"},
    "impacket":          {"dir": "impacket",            "git": False, "label": "Impacket (plain)"},
    "rubeus":            {"dir": "rubeus",              "git": False, "label": "Rubeus (plain)"},
    "mimikatz":          {"dir": "mimikatz",            "git": False, "label": "Mimikatz (plain)"},
    "bloodhound":        {"dir": "bloodhound",          "git": False, "label": "BloodHound (plain — hand-maintained)"},
    "msfvenom":          {"dir": "msfvenom",            "git": False, "label": "msfvenom (plain)"},
}


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def _git_fetch(src_dir: Path) -> tuple[int, str, str]:
    return _run(["git", "fetch", "--quiet"], cwd=src_dir)


def _git_log_ahead(src_dir: Path) -> str:
    """Return one-line log of commits on origin that aren't local yet."""
    _, out, _ = _run(["git", "log", "HEAD..origin/HEAD", "--oneline", "--no-decorate"], cwd=src_dir)
    return out


def _git_pull(src_dir: Path) -> tuple[int, str, str]:
    return _run(["git", "pull", "--ff-only", "--stat"], cwd=src_dir, timeout=300)


def _git_current_commit(src_dir: Path) -> str:
    _, out, _ = _run(["git", "rev-parse", "--short", "HEAD"], cwd=src_dir)
    return out or "unknown"


def _git_changed_files(src_dir: Path, before: str, after: str) -> list[str]:
    """Files that changed between two commits."""
    _, out, _ = _run(["git", "diff", "--name-only", before, after], cwd=src_dir)
    return [l for l in out.splitlines() if l]


app = Server("p3ta-tricks-maintenance")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="check_updates",
            description=(
                "Check all p3ta-tricks git sources for upstream changes without pulling. "
                "Returns which sources have new commits and a summary of what changed. "
                "Use this before pulling to see what's available."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="pull_updates",
            description=(
                "Pull latest changes from upstream for one or all git sources. "
                "After pulling, automatically rebuilds the search index. "
                "Pass source_ids as a list to update specific sources, or omit/empty to update all."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Source IDs to update (e.g. ['hacktricks', 'gtfobins']). Omit for all.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="rebuild_index",
            description="Rebuild the p3ta-tricks search index (scripts/build.py). Run after any content changes.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="restart_server",
            description="Restart the p3ta-tricks Flask server (kills port 5000 and relaunches app.py in background).",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="source_status",
            description="Show current commit and git status for all sources. Useful for a quick health check.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="update_all",
            description=(
                "Full maintenance run: fetch all sources, pull changes, rebuild index, restart server. "
                "This is the tool to call when the user says 'update p3ta-tricks'. "
                "Returns a summary of every source that changed with file counts."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_sources",
            description="List all registered sources with their type (git-tracked vs plain), directory, and label.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "list_sources":
        lines = ["## p3ta-tricks Sources\n"]
        for sid, cfg in SOURCE_REGISTRY.items():
            d = SOURCES / cfg["dir"]
            exists = "✓" if d.exists() else "✗ missing"
            git_tag = "git" if cfg["git"] else "plain"
            lines.append(f"- **{sid}** ({git_tag}) — {cfg['label']} — `sources/{cfg['dir']}` {exists}")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "source_status":
        lines = [f"## Source Status — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        for sid, cfg in SOURCE_REGISTRY.items():
            d = SOURCES / cfg["dir"]
            if not d.exists():
                lines.append(f"- **{sid}**: directory missing")
                continue
            if not cfg["git"]:
                lines.append(f"- **{sid}** (plain): no git tracking")
                continue
            commit = _git_current_commit(d)
            _, status_out, _ = _run(["git", "status", "--short"], cwd=d)
            local_changes = len(status_out.splitlines()) if status_out else 0
            lines.append(f"- **{sid}**: `{commit}` | {local_changes} local changes")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "check_updates":
        lines = [f"## Checking upstream — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        has_updates = []
        for sid, cfg in SOURCE_REGISTRY.items():
            d = SOURCES / cfg["dir"]
            if not cfg["git"] or not d.exists():
                continue
            rc, _, err = _git_fetch(d)
            if rc != 0:
                lines.append(f"- **{sid}**: fetch failed — {err}")
                continue
            ahead = _git_log_ahead(d)
            if ahead:
                count = len(ahead.splitlines())
                has_updates.append(sid)
                lines.append(f"- **{sid}**: {count} new commit{'s' if count > 1 else ''}")
                for l in ahead.splitlines()[:5]:
                    lines.append(f"  - {l}")
                if count > 5:
                    lines.append(f"  - … and {count - 5} more")
            else:
                lines.append(f"- **{sid}**: up to date")

        if has_updates:
            lines.append(f"\n**{len(has_updates)} source(s) have updates:** {', '.join(has_updates)}")
            lines.append("\nRun `pull_updates` or `update_all` to apply.")
        else:
            lines.append("\nAll sources are up to date.")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "pull_updates":
        requested = arguments.get("source_ids") or []
        targets = {sid: cfg for sid, cfg in SOURCE_REGISTRY.items()
                   if cfg["git"] and (not requested or sid in requested)}

        lines = [f"## Pulling updates — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        changed_any = False

        for sid, cfg in targets.items():
            d = SOURCES / cfg["dir"]
            if not d.exists():
                lines.append(f"- **{sid}**: directory missing, skipping")
                continue
            before = _git_current_commit(d)
            _git_fetch(d)
            rc, out, err = _git_pull(d)
            after = _git_current_commit(d)
            if rc != 0:
                lines.append(f"- **{sid}**: pull failed — {err}")
            elif before == after:
                lines.append(f"- **{sid}**: already up to date (`{before}`)")
            else:
                changed = _git_changed_files(d, before, after)
                changed_any = True
                lines.append(f"- **{sid}**: `{before}` → `{after}` | {len(changed)} files changed")
                for f in changed[:8]:
                    lines.append(f"  - {f}")
                if len(changed) > 8:
                    lines.append(f"  - … and {len(changed) - 8} more")

        if changed_any:
            lines.append("\n---\nRebuilding search index…")
            rc, out, err = _run([sys.executable, str(BUILD_SCRIPT)], timeout=300)
            if rc == 0:
                lines.append("Index rebuilt successfully.")
            else:
                lines.append(f"Index rebuild failed:\n```\n{err}\n```")
        else:
            lines.append("\nNo changes — index rebuild skipped.")

        return [TextContent(type="text", text="\n".join(lines))]

    if name == "rebuild_index":
        lines = [f"## Rebuilding index — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        rc, out, err = _run([sys.executable, str(BUILD_SCRIPT)], timeout=300)
        if rc == 0:
            # Parse the INFO lines for page counts
            counts = [l for l in out.splitlines() if "INFO" in l and l.strip().split()[-1].isdigit()]
            lines.append("Index rebuilt successfully.\n")
            for c in counts:
                lines.append(f"  {c.split('INFO:')[-1].strip()}")
        else:
            lines.append(f"Build failed:\n```\n{err}\n```")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "restart_server":
        _run(["bash", "-c", "kill $(lsof -ti:5000) 2>/dev/null; true"])
        await asyncio.sleep(1)
        subprocess.Popen(
            [sys.executable, str(ROOT / "app.py")],
            stdout=open("/tmp/p3ta-flask.log", "w"),
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )
        await asyncio.sleep(2)
        rc, out, _ = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:5000/"])
        status = "✓ server responding (HTTP 200)" if out == "200" else f"⚠ HTTP {out}"
        return [TextContent(type="text", text=f"Server restarted. {status}\nLog: /tmp/p3ta-flask.log")]

    if name == "update_all":
        lines = [f"# p3ta-tricks Full Update — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        changed_sources = []

        # Step 1: fetch + pull all git sources
        lines.append("## Step 1: Pulling all sources\n")
        for sid, cfg in SOURCE_REGISTRY.items():
            if not cfg["git"]:
                continue
            d = SOURCES / cfg["dir"]
            if not d.exists():
                lines.append(f"- **{sid}**: missing")
                continue
            before = _git_current_commit(d)
            _git_fetch(d)
            rc, out, err = _git_pull(d)
            after = _git_current_commit(d)
            if rc != 0:
                lines.append(f"- **{sid}**: ⚠ pull failed — {err[:80]}")
            elif before == after:
                lines.append(f"- **{sid}**: up to date")
            else:
                changed = _git_changed_files(d, before, after)
                changed_sources.append((sid, len(changed)))
                lines.append(f"- **{sid}**: ✓ {len(changed)} file(s) changed (`{before[:7]}` → `{after[:7]}`)")
                for f in changed[:5]:
                    lines.append(f"  - {f}")
                if len(changed) > 5:
                    lines.append(f"  - … +{len(changed) - 5} more")

        # Step 2: rebuild index
        lines.append("\n## Step 2: Rebuilding index\n")
        rc, out, err = _run([sys.executable, str(BUILD_SCRIPT)], timeout=300)
        if rc == 0:
            counts = [l.split("INFO:")[-1].strip() for l in out.splitlines() if "INFO" in l and l.strip().split()[-1].isdigit()]
            lines.append("Index rebuilt. Page counts:")
            for c in counts:
                lines.append(f"  {c}")
        else:
            lines.append(f"⚠ Build failed:\n```\n{err[:500]}\n```")

        # Step 3: restart server
        lines.append("\n## Step 3: Restarting server\n")
        _run(["bash", "-c", "kill $(lsof -ti:5000) 2>/dev/null; true"])
        await asyncio.sleep(1)
        subprocess.Popen(
            [sys.executable, str(ROOT / "app.py")],
            stdout=open("/tmp/p3ta-flask.log", "w"),
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )
        await asyncio.sleep(2)
        rc2, code, _ = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:5000/"])
        lines.append("✓ Server restarted." if code == "200" else f"⚠ Server may not be up (HTTP {code})")

        # Summary
        lines.append(f"\n## Summary\n")
        if changed_sources:
            lines.append(f"{len(changed_sources)} source(s) updated: " + ", ".join(f"{s} ({n} files)" for s, n in changed_sources))
        else:
            lines.append("All sources were already up to date.")

        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
