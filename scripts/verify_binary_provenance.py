#!/usr/bin/env python3
"""Verify every file declared in binaries/.provenance.json."""
from pathlib import Path
import hashlib, json, sys
root = Path(__file__).resolve().parent.parent / "binaries"
manifest = root / ".provenance.json"
if not manifest.is_file():
    sys.exit("missing binaries/.provenance.json")
data = json.loads(manifest.read_text(encoding="utf-8"))
expected = data.get("files", [])
seen = set()
for item in expected:
    rel = item["path"]
    path = root / rel
    if not path.is_file():
        sys.exit(f"missing binary: {rel}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item["sha256"]:
        sys.exit(f"checksum mismatch: {rel}")
    if path.stat().st_size != item["size"]:
        sys.exit(f"size mismatch: {rel}")
    seen.add(rel)
actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != ".provenance.json"}
extra = sorted(actual - seen)
if extra:
    sys.exit("unrecorded binary files: " + ", ".join(extra))
print(f"Verified {len(expected)} binary files against provenance manifest")
