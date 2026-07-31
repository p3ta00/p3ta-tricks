#!/usr/bin/env python3
"""Post-render hook for rebuild_sources.py.

Copy buttons are attached client-side (static/js/app.js walks every
`div.highlight` after the page loads), so nothing needs to be baked into the
stored HTML. This stays as an explicit pass-through because rebuild_sources.py
imports it, and because it is the right seam if copy markup ever has to move
back into the build.

Verified no-op: re-rendering a tracked source page through this pipeline
reproduces its committed content/processed JSON byte for byte.
"""


def inject_copy_blocks(html: str) -> str:
    return html


if __name__ == "__main__":
    import sys
    sys.stdout.write(inject_copy_blocks(sys.stdin.read()))
