#!/usr/bin/env python3
"""
Download third-party images embedded in processed content and serve them locally.

For every <img src="https://..."> in content/processed/**/*.json that isn't
already local or GitHub-raw:
  1. Attempt to download the image
  2. Save to static/img/external/<hash>.<ext>
  3. Patch the JSON HTML in-place: replace the external src with /static/img/external/...

Skips decorative/badge images (shields.io, repobeats, contrib.rocks, etc.).
Converts github.com/blob/ links to raw.githubusercontent.com automatically.
Idempotent — already-downloaded images are skipped.

Usage:
    python3 scripts/fetch_external_images.py
    python3 scripts/fetch_external_images.py --dry-run
"""
import re, sys, json, time, hashlib, urllib.request, urllib.parse
from pathlib import Path

ROOT       = Path(__file__).parent.parent
PROCESSED  = ROOT / "content" / "processed"
OUT_DIR    = ROOT / "static" / "img" / "external"
UA         = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"
DRY_RUN    = "--dry-run" in sys.argv

OUT_DIR.mkdir(parents=True, exist_ok=True)

IMG_RE = re.compile(r'(<img\b[^>]*\bsrc=)([\"\'])(https?://[^\"\']+)\2', re.I)

# Domains that are decorative/tracking — skip entirely
SKIP_DOMAINS = {
    "img.shields.io",
    "shields.io",
    "repobeats.axiom.co",
    "contrib.rocks",
    "visitor-badge.glitch.me",
    "hits.seeyoufarm.com",
    "komarev.com",
    "img.buymeacoffee.com",
    "badgen.net",
    "flat.badgen.net",
}


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


def _to_raw(url: str) -> str:
    """Convert github.com/owner/repo/blob/branch/path to raw.githubusercontent.com."""
    m = re.match(
        r'https?://github\.com/([^/]+/[^/]+)/blob/([^/]+)/(.+)',
        url
    )
    if m:
        return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}"
    # user-attachments are served directly
    return url


def _ext_from_url(url: str, content_type: str = "") -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
        if path.endswith(f".{ext}"):
            return "jpg" if ext == "jpeg" else ext
    if "png" in content_type:  return "png"
    if "jpeg" in content_type or "jpg" in content_type: return "jpg"
    if "gif" in content_type:  return "gif"
    if "webp" in content_type: return "webp"
    if "svg" in content_type:  return "svg"
    return "png"


def _local_name(url: str, ext: str) -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:16]
    return f"{h}.{ext}"


def download(url: str) -> tuple[bytes, str]:
    """Returns (data, content_type) or raises."""
    raw_url = _to_raw(url)
    req = urllib.request.Request(raw_url, headers={
        "User-Agent": UA,
        "Accept": "image/*,*/*",
        "Referer": "https://p3ta-tricks.com/",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        ct = r.headers.get("Content-Type", "")
        data = r.read()
    return data, ct


def is_image(data: bytes, ct: str) -> bool:
    magic = data[:8]
    if magic[:4] in (b"\x89PNG", b"GIF8", b"RIFF") or magic[:2] == b"\xff\xd8":
        return True
    if magic[:4] == b"<svg" or b"<svg" in data[:64]:
        return True
    if b"WEBP" in magic:
        return True
    if "image/" in ct:
        return True
    return False


def process_json(fpath: Path, stats: dict, url_cache: dict) -> bool:
    """Patch one JSON file. Returns True if modified."""
    raw = fpath.read_text(encoding="utf-8")
    data = json.loads(raw)
    html = data.get("html", "")
    if not html:
        return False

    new_html = html
    changed = False

    for m in IMG_RE.finditer(html):
        prefix, q, url = m.group(1), m.group(2), m.group(3)
        dom = _domain(url)

        if dom in SKIP_DOMAINS:
            stats["skipped_badge"] += 1
            continue

        # Already replaced in a previous run or earlier in this file
        if url in url_cache:
            local_path = url_cache[url]
            if local_path:
                new_html = new_html.replace(
                    f"{prefix}{q}{url}{q}",
                    f"{prefix}{q}{local_path}{q}",
                    1,
                )
                changed = True
            stats["cached"] += 1
            continue

        # Determine local filename (use md5 of original URL for stability)
        raw_url = _to_raw(url)
        ext_guess = _ext_from_url(url)
        local_name = _local_name(url, ext_guess)
        dest = OUT_DIR / local_name
        local_path = f"/static/img/external/{local_name}"

        if dest.exists():
            url_cache[url] = local_path
            new_html = new_html.replace(
                f"{prefix}{q}{url}{q}",
                f"{prefix}{q}{local_path}{q}",
                1,
            )
            changed = True
            stats["already_cached"] += 1
            continue

        if DRY_RUN:
            print(f"  DRY: {url[:80]}")
            stats["would_download"] += 1
            url_cache[url] = None
            continue

        try:
            img_data, ct = download(url)
            if not is_image(img_data, ct):
                print(f"  SKIP (not image, {len(img_data)}b): {url[:80]}")
                stats["not_image"] += 1
                url_cache[url] = None
                continue

            # Re-guess extension from actual content-type
            ext = _ext_from_url(url, ct)
            if ext != ext_guess:
                local_name = _local_name(url, ext)
                dest = OUT_DIR / local_name
                local_path = f"/static/img/external/{local_name}"

            dest.write_bytes(img_data)
            url_cache[url] = local_path
            new_html = new_html.replace(
                f"{prefix}{q}{url}{q}",
                f"{prefix}{q}{local_path}{q}",
                1,
            )
            changed = True
            stats["downloaded"] += 1
            print(f"  OK ({len(img_data)//1024}KB): {url[:80]}")
            time.sleep(0.2)

        except Exception as e:
            stats["errors"] += 1
            url_cache[url] = None
            print(f"  ERR ({type(e).__name__}): {url[:80]}")

    # Never leave a broken or tracking image as a live remote subresource. If
    # an image was decorative, blocked, or no longer recoverable, remove the
    # complete tag after all recoverable images have been localized.
    cleaned = re.sub(
        r'<img\b[^>]*\bsrc=(["\'])https?://[^"\']+\1[^>]*>',
        '', new_html, flags=re.I,
    )
    if cleaned != new_html:
        new_html = cleaned
        changed = True
        stats.setdefault("removed_unrecoverable", 0)
        stats["removed_unrecoverable"] += 1

    if changed and not DRY_RUN:
        data["html"] = new_html
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    return changed


def main():
    print(f"Scanning {PROCESSED} for external images...")
    print(f"Output: {OUT_DIR}")
    if DRY_RUN:
        print("DRY RUN — no files will be written\n")

    stats = {
        "downloaded": 0,
        "already_cached": 0,
        "cached": 0,
        "skipped_badge": 0,
        "not_image": 0,
        "errors": 0,
        "would_download": 0,
        "files_patched": 0,
    }
    url_cache: dict = {}  # url -> local_path or None

    all_json = sorted(PROCESSED.rglob("*.json"))
    print(f"Checking {len(all_json)} JSON files...\n")

    for fpath in all_json:
        if process_json(fpath, stats, url_cache):
            stats["files_patched"] += 1

    print(f"\n{'='*60}")
    print(f"Downloaded:      {stats['downloaded']}")
    print(f"Already cached:  {stats['already_cached']}")
    print(f"Skipped (badge): {stats['skipped_badge']}")
    print(f"Not an image:    {stats['not_image']}")
    print(f"Errors:          {stats['errors']}")
    print(f"Cleaned files:   {stats.get('removed_unrecoverable', 0)}")
    if DRY_RUN:
        print(f"Would download:  {stats['would_download']}")
    print(f"Files patched:   {stats['files_patched']}")
    total = len(list(OUT_DIR.glob("*")))
    print(f"Total cached:    {total} images in {OUT_DIR}")


if __name__ == "__main__":
    main()
