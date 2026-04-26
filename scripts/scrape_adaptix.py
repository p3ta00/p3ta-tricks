#!/usr/bin/env python3
"""
Scrape Adaptix Framework GitBook docs via the GitBook content API.

Strategy:
1. Fetch sitemap for URL ordering / titles (for SUMMARY.md)
2. Fetch the space content index to get page paths -> documentIds
3. For each page, fetch document JSON from the content API
4. Convert GitBook node tree -> Markdown
5. Save per-page .md files mirroring the URL path
6. Write SUMMARY.md
"""

import re
import sys
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
SITEMAP_URL  = "https://adaptix-framework.gitbook.io/adaptix-framework/sitemap-pages.xml"
BASE_URL     = "https://adaptix-framework.gitbook.io/adaptix-framework"
SPACE_ID     = "S8p8XLFtLmf0NkofQvoa"
API_BASE     = f"https://api.gitbook.com/v1/spaces/{SPACE_ID}"
OUT_DIR      = Path("/home/p3ta/p3ta-tricks/sources/adaptix")
DELAY        = 0.5
UA           = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def http_get(url: str, headers: dict = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_api(path: str, token: str, retries: int = 3) -> dict:
    url = API_BASE + path
    last_err = None
    for attempt in range(retries):
        try:
            data = http_get(url, {"Authorization": f"Bearer {token}"})
            return json.loads(data)
        except Exception as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # exponential backoff
    raise last_err


# ── Token extraction ──────────────────────────────────────────────────────────

def get_api_token() -> str:
    """Extract the short-lived content API token embedded in the GitBook page."""
    html = http_get(BASE_URL).decode("utf-8", errors="replace")
    m = re.search(r'apiToken%3A(eyJ[A-Za-z0-9._-]+)', html)
    if not m:
        raise RuntimeError("Could not extract API token from GitBook page")
    return m.group(1)


# ── Page tree ─────────────────────────────────────────────────────────────────

def flatten_pages(pages: list, result: list = None) -> list:
    """Recursively flatten nested page tree into a list of (path, title, documentId)."""
    if result is None:
        result = []
    for p in pages:
        path     = p.get("path", "")
        title    = p.get("title", "")
        doc_id   = p.get("documentId")  # may be None for group-level pages
        result.append({"path": path, "title": title, "documentId": doc_id})
        if p.get("pages"):
            flatten_pages(p["pages"], result)
    return result


# ── GitBook node -> Markdown ──────────────────────────────────────────────────

MARK_WRAPPERS = {
    "bold":          ("**", "**"),
    "italic":        ("_",  "_"),
    "code":          ("`",  "`"),
    "strikethrough": ("~~", "~~"),
    "underline":     ("",   ""),   # no MD equivalent, skip
}


def leaves_to_text(leaves: list) -> str:
    parts = []
    for leaf in leaves:
        text  = leaf.get("text", "")
        marks = [m["type"] for m in leaf.get("marks", [])]
        # Apply mark wrappers inside-out (innermost first)
        for mark in reversed(marks):
            pre, suf = MARK_WRAPPERS.get(mark, ("", ""))
            text = pre + text + suf
        parts.append(text)
    return "".join(parts)


def inline_to_md(node: dict) -> str:
    itype = node.get("type", "")
    inner = nodes_to_md(node.get("nodes", []))
    if itype == "link":
        url = node.get("data", {}).get("ref", {}).get("url", "")
        if url:
            return f"[{inner}]({url})"
        return inner
    if itype == "math":
        return f"${inner}$"
    return inner


def nodes_to_md(nodes: list) -> str:
    """Convert a list of inline/text nodes to a markdown string."""
    parts = []
    for n in nodes:
        obj = n.get("object")
        if obj == "text":
            parts.append(leaves_to_text(n.get("leaves", [])))
        elif obj == "inline":
            parts.append(inline_to_md(n))
        elif obj == "block":
            # nested block inside inline context (rare)
            parts.append(block_to_md(n))
    return "".join(parts)


def block_to_md(node: dict) -> str:  # noqa: C901 (complexity ok here)
    btype  = node.get("type", "")
    data   = node.get("data", {})
    children = node.get("nodes", [])

    # ── Headings ──────────────────────────────────────────────────────────────
    if btype == "heading-1":
        return f"# {nodes_to_md(children)}\n\n"
    if btype == "heading-2":
        return f"## {nodes_to_md(children)}\n\n"
    if btype == "heading-3":
        return f"### {nodes_to_md(children)}\n\n"
    if btype == "heading-4":
        return f"#### {nodes_to_md(children)}\n\n"
    if btype == "heading-5":
        return f"##### {nodes_to_md(children)}\n\n"
    if btype == "heading-6":
        return f"###### {nodes_to_md(children)}\n\n"

    # ── Paragraph ─────────────────────────────────────────────────────────────
    if btype == "paragraph":
        text = nodes_to_md(children).strip()
        if not text:
            return "\n"
        return f"{text}\n\n"

    # ── Code block ────────────────────────────────────────────────────────────
    if btype == "code":
        lang  = data.get("syntax", "")
        lines = []
        for child in children:
            if child.get("type") == "code-line":
                lines.append(nodes_to_md(child.get("nodes", [])))
        return f"```{lang}\n" + "\n".join(lines) + "\n```\n\n"

    # ── Lists ─────────────────────────────────────────────────────────────────
    if btype == "list-unordered":
        parts = []
        for item in children:
            if item.get("type") == "list-item":
                item_md = list_item_to_md(item, bullet="- ")
                parts.append(item_md)
        return "".join(parts) + "\n"

    if btype == "list-ordered":
        parts = []
        for i, item in enumerate(children, 1):
            if item.get("type") == "list-item":
                item_md = list_item_to_md(item, bullet=f"{i}. ")
                parts.append(item_md)
        return "".join(parts) + "\n"

    # ── Hint / callout ────────────────────────────────────────────────────────
    if btype == "hint":
        style = data.get("style", "info").upper()
        inner = "".join(block_to_md(c) for c in children if c.get("object") == "block")
        # Blockquote with label
        prefixed = "\n".join(f"> {line}" for line in inner.splitlines())
        return f"> **{style}**\n{prefixed}\n\n"

    # ── Quote ─────────────────────────────────────────────────────────────────
    if btype == "quote":
        inner = nodes_to_md(children).strip()
        lines = "\n".join(f"> {l}" for l in inner.splitlines())
        return f"{lines}\n\n"

    # ── Table ─────────────────────────────────────────────────────────────────
    if btype == "table":
        return table_to_md(node) + "\n"

    # ── Divider ───────────────────────────────────────────────────────────────
    if btype in ("divider", "hr"):
        return "---\n\n"

    # ── Image ─────────────────────────────────────────────────────────────────
    if btype == "image":
        alt = data.get("alt", "")
        url = data.get("ref", {}).get("url", "")
        if not url:
            # GitBook stores images as file refs - emit a placeholder
            file_ref = data.get("ref", {}).get("file", "")
            if file_ref:
                return f"![{alt}](<!-- gitbook-image:{file_ref} -->)\n\n"
        return f"![{alt}]({url})\n\n"

    if btype == "images":
        parts = []
        for child in children:
            if child.get("type") == "image":
                parts.append(block_to_md(child))
        return "".join(parts)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    if btype == "tabs":
        parts = []
        for tab in children:
            if tab.get("type") == "tab":
                tab_title = tab.get("data", {}).get("title", "Tab")
                tab_content = "".join(
                    block_to_md(c) for c in tab.get("nodes", [])
                    if c.get("object") == "block"
                )
                parts.append(f"**{tab_title}**\n\n{tab_content}")
        return "".join(parts)

    # ── Expandable ────────────────────────────────────────────────────────────
    if btype in ("expandable", "details"):
        title = nodes_to_md(
            next((c.get("nodes", []) for c in children
                  if c.get("type") in ("expandable-title", "summary")), [])
        ).strip()
        body  = "".join(
            block_to_md(c) for c in children
            if c.get("type") not in ("expandable-title", "summary")
            and c.get("object") == "block"
        )
        return f"<details><summary>{title}</summary>\n\n{body}</details>\n\n"

    # ── File / embed  ─────────────────────────────────────────────────────────
    if btype in ("file", "embed"):
        url = data.get("ref", {}).get("url", data.get("url", ""))
        name = data.get("name", url)
        if url:
            return f"[{name}]({url})\n\n"
        return ""

    # ── Math block ────────────────────────────────────────────────────────────
    if btype == "math":
        inner = nodes_to_md(children).strip()
        return f"$$\n{inner}\n$$\n\n"

    # ── Reusable content ──────────────────────────────────────────────────────
    if btype == "reusable-content":
        inner = "".join(
            block_to_md(c) for c in children if c.get("object") == "block"
        )
        return inner

    # ── Fallback: recurse into children ──────────────────────────────────────
    parts = []
    for child in children:
        obj = child.get("object")
        if obj == "block":
            parts.append(block_to_md(child))
        elif obj in ("text", "inline"):
            parts.append(nodes_to_md([child]))
    return "".join(parts)


def list_item_to_md(item: dict, bullet: str, indent: int = 0) -> str:
    prefix = "  " * indent
    parts  = []
    for child in item.get("nodes", []):
        ctype = child.get("type", "")
        if ctype in ("paragraph", "heading-1", "heading-2",
                     "heading-3", "heading-4", "heading-5", "heading-6"):
            text = nodes_to_md(child.get("nodes", [])).strip()
            parts.append(f"{prefix}{bullet}{text}\n")
        elif ctype == "list-unordered":
            for sub in child.get("nodes", []):
                if sub.get("type") == "list-item":
                    parts.append(list_item_to_md(sub, bullet="- ", indent=indent+1))
        elif ctype == "list-ordered":
            for i2, sub in enumerate(child.get("nodes", []), 1):
                if sub.get("type") == "list-item":
                    parts.append(list_item_to_md(sub, bullet=f"{i2}. ", indent=indent+1))
        elif child.get("object") == "block":
            inner = block_to_md(child).rstrip()
            parts.append(f"{prefix}  {inner}\n")
    return "".join(parts) if parts else f"{prefix}{bullet}\n"


def table_to_md(node: dict) -> str:
    rows  = []
    header_done = False
    for child in node.get("nodes", []):
        if child.get("type") != "table-row":
            continue
        cells = []
        for cell in child.get("nodes", []):
            if cell.get("type") not in ("table-cell", "table-header"):
                continue
            cell_text = "".join(
                block_to_md(c) if c.get("object") == "block" else nodes_to_md([c])
                for c in cell.get("nodes", [])
            ).replace("\n", " ").strip()
            cells.append(cell_text)
        if not cells:
            continue
        rows.append("| " + " | ".join(cells) + " |")
        if not header_done:
            rows.append("|" + "|".join(" --- " for _ in cells) + "|")
            header_done = True
    return "\n".join(rows) + "\n"


def document_to_md(title: str, doc: dict) -> str:
    """Convert a full GitBook document JSON to Markdown."""
    parts = [f"# {title}\n\n"] if title else []
    for node in doc.get("nodes", []):
        obj = node.get("object")
        if obj == "block":
            parts.append(block_to_md(node))
        elif obj in ("text", "inline"):
            parts.append(nodes_to_md([node]))
    return "".join(parts)


# ── Path helper ───────────────────────────────────────────────────────────────

def path_to_file(page_path: str) -> Path:
    """Convert a GitBook page path to an output .md file path."""
    if not page_path or page_path == "readme":
        return OUT_DIR / "README.md"
    return OUT_DIR / (page_path.replace("/", "__") + ".md") if False else \
           OUT_DIR / Path(page_path.replace("-", "_") if False else page_path + ".md")


def safe_filename(page_path: str) -> Path:
    """Mirror URL path as directory structure."""
    if not page_path or page_path in ("readme", ""):
        return OUT_DIR / "README.md"
    parts = page_path.split("/")
    p = OUT_DIR
    for part in parts[:-1]:
        p = p / part
    return p / (parts[-1] + ".md")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[*] Fetching API token...")
    token = get_api_token()
    print(f"    Token: {token[:40]}...")

    print("[*] Fetching space content index...")
    content = fetch_api("/content", token)
    all_pages = flatten_pages(content.get("pages", []))
    print(f"    Found {len(all_pages)} pages in content index")
    time.sleep(DELAY)

    # Build path->title map from sitemap (in case API title differs)
    # Also get the authoritative URL order
    print("[*] Fetching sitemap for URL ordering...")
    sitemap_xml = http_get(SITEMAP_URL).decode("utf-8", errors="replace")
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.fromstring(sitemap_xml)
    sitemap_urls = []
    prefix = "https://adaptix-framework.gitbook.io/adaptix-framework"
    for url_el in root.findall(f"{{{ns}}}url"):
        loc = url_el.findtext(f"{{{ns}}}loc", "").strip()
        if loc.startswith(prefix):
            page_path = loc[len(prefix):].lstrip("/")
            if not page_path:
                page_path = "readme"
            sitemap_urls.append(page_path)
    print(f"    Sitemap has {len(sitemap_urls)} URLs")

    # Build a lookup: path -> page info
    page_map = {p["path"]: p for p in all_pages}

    # Merge: use sitemap order, supplement with content index
    ordered_pages = []
    seen = set()
    for sp in sitemap_urls:
        key = sp if sp else "readme"
        if key in page_map and key not in seen:
            ordered_pages.append(page_map[key])
            seen.add(key)
    # Add any pages in content index not in sitemap
    for p in all_pages:
        if p["path"] not in seen:
            ordered_pages.append(p)
            seen.add(p["path"])

    print(f"[*] Processing {len(ordered_pages)} pages...")
    saved = 0
    skipped = 0
    errors  = []
    summary_lines = ["# Adaptix Framework Docs - Summary\n\n"]

    for page in ordered_pages:
        path    = page["path"]
        title   = page["title"]
        doc_id  = page["documentId"]
        out_file = safe_filename(path)

        indent = "  " * (path.count("/"))
        summary_lines.append(f"{indent}- [{title}]({path}.md)\n")

        if not doc_id:
            # Group-level page with no content
            print(f"  [skip] {path} (no documentId)")
            skipped += 1
            continue

        print(f"  [fetch] {path} (doc:{doc_id})")
        try:
            doc = fetch_api(f"/documents/{doc_id}", token)
            md  = document_to_md(title, doc)

            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(md, encoding="utf-8")
            saved += 1
            print(f"         -> {out_file.relative_to(OUT_DIR)} ({len(md)} chars)")
        except Exception as exc:
            print(f"  [ERROR] {path}: {exc}")
            errors.append((path, str(exc)))
        time.sleep(DELAY)

    # Write SUMMARY.md
    summary_path = OUT_DIR / "SUMMARY.md"
    summary_path.write_text("".join(summary_lines), encoding="utf-8")
    print(f"\n[*] SUMMARY.md written to {summary_path}")

    print(f"\n{'='*60}")
    print(f"  Saved:   {saved} pages")
    print(f"  Skipped: {skipped} (group pages, no content)")
    if errors:
        print(f"  Errors:  {len(errors)}")
        for path, err in errors:
            print(f"    - {path}: {err}")
    print(f"  Output:  {OUT_DIR}")
    print(f"{'='*60}")

    return saved


if __name__ == "__main__":
    saved = main()
    sys.exit(0 if saved > 0 else 1)
