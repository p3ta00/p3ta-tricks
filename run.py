#!/usr/bin/env python3
"""
p3ta-tricks launcher.

Usage:
    python3 run.py              # start server (build if index missing)
    python3 run.py --rebuild    # force rebuild of content index before starting
    python3 run.py --build-only # build index then exit (no server)
"""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
os.chdir(BASE_DIR)

SEARCH_INDEX = BASE_DIR / "static" / "search_index.json"
BUILD_SCRIPT = BASE_DIR / "scripts" / "build.py"
ADD_CONTENT_SCRIPT = BASE_DIR / "scripts" / "add_content.py"


def _run_build(force: bool = False) -> None:
    if force or not SEARCH_INDEX.exists():
        print(f"[run.py] {'Force-rebuilding' if force else 'Building'} content index…")
        result = subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=False)
        if result.returncode != 0:
            print("[run.py] ERROR: build.py exited with non-zero status.")
            sys.exit(result.returncode)
        # Add built-in reference content and merge into search index
        result2 = subprocess.run([sys.executable, str(ADD_CONTENT_SCRIPT)], check=False)
        if result2.returncode != 0:
            print("[run.py] WARNING: add_content.py exited with non-zero status.")


def main() -> None:
    force_rebuild = "--rebuild" in sys.argv
    build_only = "--build-only" in sys.argv

    _run_build(force=force_rebuild)

    if build_only:
        print("[run.py] Build complete. Exiting (--build-only).")
        return

    # Import here so the module loads after the build is done
    from app import app  # noqa: PLC0415

    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    print(f"[run.py] Starting p3ta-tricks on http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
