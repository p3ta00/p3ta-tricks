#!/usr/bin/env python3
"""Gate a rebuild: prove the build pipeline still reproduces committed content.

The build is only as trustworthy as its hooks. scripts/inject_variable_tokens.py
is a reconstruction of a lost original (see its docstring), so a rebuild can
quietly rewrite thousands of pages that upstream never touched -- stripping the
`<TARGET>`/`<USERNAME>` placeholders the whole variables feature depends on.

This rebuilds each source into a temp directory and compares against the
committed JSON. A real weekly pull moves a handful of pages; anything above
--max-churn means the pipeline, not upstream, is what changed.

Exit 0 = safe to rebuild for real. Exit 1 = do not overwrite content/.

Usage:
    python3 scripts/check_fidelity.py netexec hacktricks [--max-churn 15]
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_hooks():
    """Import the real build hooks so the temp build matches the real one."""
    sys.path.insert(0, str(ROOT / "scripts"))
    for name in ("inject_copy_blocks", "inject_variable_tokens"):
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[name] = mod


def load_rebuild():
    spec = importlib.util.spec_from_file_location("rs", ROOT / "scripts" / "rebuild_sources.py")
    rs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rs)
    return rs


def committed(rel):
    out = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:" + rel],
                         capture_output=True, text=True, encoding="utf-8")
    return out.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--max-churn", type=float, default=15.0,
                    help="percent of a source's pages allowed to differ (default 15)")
    args = ap.parse_args()

    load_hooks()
    rs = load_rebuild()

    failed = []
    with tempfile.TemporaryDirectory() as td:
        rs.PROCESSED = Path(td)
        rs.INDEX = Path(td) / "index.json"

        for sid in args.sources:
            cfg = rs.SOURCES_CFG.get(sid)
            if not cfg:
                print(f"  [{sid}] unknown source, skipping")
                continue
            if not cfg["root"].exists():
                print(f"  [{sid}] sources/ not checked out, skipping")
                continue

            rs.build_source(sid, cfg)
            same = diff = new = 0
            for p in sorted(Path(td, sid).glob("*.json")):
                raw = committed(f"content/processed/{sid}/{p.name}")
                if not raw:
                    new += 1
                    continue
                if json.loads(raw) == json.loads(p.read_text(encoding="utf-8")):
                    same += 1
                else:
                    diff += 1

            known = same + diff
            churn = (100.0 * diff / known) if known else 0.0
            verdict = "ok" if churn <= args.max_churn else "FAIL"
            if verdict == "FAIL":
                failed.append((sid, churn))
            print(f"  [{sid}] {same} identical, {diff} changed, {new} new "
                  f"-- {churn:.1f}% churn ({verdict})")

    if failed:
        print()
        print("[!] Rebuild refused. These sources churn more than a weekly pull can explain:")
        for sid, churn in failed:
            print(f"      {sid}: {churn:.1f}%")
        print("    That is the build pipeline changing, not upstream. Most likely")
        print("    scripts/inject_variable_tokens.py -- see its docstring.")
        print("    Override with --max-churn if you are certain upstream really moved.")
        return 1

    print("[+] Pipeline reproduces committed content. Safe to rebuild.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
