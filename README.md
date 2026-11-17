# p3ta-tricks

> If this saves you time on an engagement, please ⭐ star the repo — it helps more than you think.
>
> Feature requests, bugs, and ideas → Discord: **p3ta00**

---

A fast, searchable pentest reference that pulls attack techniques, tool syntax, and post-exploitation chains from the best open-source security wikis into one place. No more tab switching mid-engagement.

**Live site → [p3ta-tricks.com](https://p3ta-tricks.com)**

---

## Local development

The online repository commits all rendered documentation, navigation data, search
indexes, and recoverable documentation media. Current media inventory:

- **`static/source-assets/`** — 1,519 source-relative documentation assets.
- **`static/img/external/`** — 1,668 recovered third-party images.
- Automatically loaded remote documentation images: **0**.

The separately published
[`p3ta-tricks-offline`](https://github.com/p3ta00/p3ta-tricks-offline)
release additionally vendors Python packages, compiled tools, and the complete
Exploit-DB source corpus for a machine that will never have internet access.

### Quick start

```bash
chmod +x install.sh && ./install.sh
./start-offline.sh
# open http://127.0.0.1:5001
```

Custom port / host:
```bash
PORT=8080 HOST=0.0.0.0 ./start-offline.sh
```

The installer handles the Python environment and dependencies. Generated content
and documentation assets are already committed; installation does not rebuild them.

---

## What's in it

BloodHound · HackTricks · HackTricks Cloud · The Hacker Recipes · PayloadsAllTheThings · InternalAllTheThings · HardwareAllTheThings · GTFOBins · LOLBAS · WADComs · NetExec · Impacket · Certipy · bloodyAD · Rubeus · Mimikatz · Ligolo-ng · Sliver · Adaptix C2 · goexec · Metasploit · All About Bug Bounty · Exploit-DB · Church of Malware · Misc Cheatsheets

**4,975 pages · 36 sources**

Exploit-DB is pinned separately from the page search corpus: **47,182 raw upstream
CSV rows**, normalized to **46,710 unique locally addressable records**. The current
snapshot is database revision **2026-11-12**, commit
`70bbef3f18b835b0d8bacb978f2bc7b751a7cec9`, newest EDB-ID **52705**.

---

## Features

**Search** — `Ctrl+K` from anywhere. Searches all sources at once and ranks by relevance.

**Variables** — Every code block uses `<placeholders>` like `<target-ip>`, `<domain>`, `<username>`. Fill them in once and they populate across every block for the session.

**Distro toggle** — Switch Impacket syntax between Kali (`impacket-secretsdump`), Exegol (`secretsdump.py`), and Script (`python3 secretsdump.py`).

**Tools toggle** — Swap between Python Impacket and Go-style equivalents site-wide.

**Themes** — Retro, Tokyo Night, Catppuccin Mocha, Catppuccin Latte, Rosé Pine, Dracula, Nord, Gruvbox, Hacker Green, Wonderland.

**Favorites** — Star any page with the ☆ button next to the title. Favorites persist in localStorage.

**Mobile friendly** — Works on phone. Sidebar drawer, full-width search, touch-sized targets.

---

## Updating

`./update.sh` is the weekly refresh. It clones or fast-forwards every upstream
wiki into `sources/` (gitignored — build inputs, not repo content), rebuilds
only the sources that actually moved, refreshes the nav caches and search index,
re-applies the local corrections, and prints the commit message to use.

```bash
./update.sh                  # pull, rebuild what changed
./update.sh --pull-only      # refresh sources/ and report, no rebuild
./update.sh --force          # rebuild every cloned source regardless
./update.sh --commit --push  # ...and ship it
```

Sources that are hand-written (`active-directory`, `cheatsheet`, the BloodHound
edge pages, `misc`, `breaking-adcs`) are deliberately left alone. The updater
refreshes the canonical Church of Malware feed and Exploit-DB CSV through their
dedicated fail-closed transforms; remaining non-automated families are printed
explicitly rather than silently treated as current.

### Known issue: the rebuild is currently gated

`scripts/inject_variable_tokens.py` — the build step that turns upstream's
literal `10.10.176.246 -u frank` into `<TARGET> -u <USERNAME>`, which is what
makes the Variables feature work — was never committed and was lost with the
machine it lived on. What's in the repo now is a reconstruction reverse-engineered
from the published content, and it is not equivalent: measured against "a page
whose upstream markdown didn't change must rebuild byte-identically" it
reproduces roughly 65% of the corpus.

So `update.sh` runs `scripts/check_fidelity.py` first and **refuses to rebuild**
while churn is that high, rather than shipping thousands of pages with their
placeholders silently reverted to someone's lab IPs. Improve the table and rules
in `inject_variable_tokens.py` until the check passes and the weekly update runs
unattended again; `--skip-check` bypasses it if you know what you're doing.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/fetch_adaptix_images.py` | Scrape GitBook CDN and download all Adaptix screenshots locally |
| `scripts/fetch_external_images.py` | Download third-party images embedded in source docs and host locally |
| `scripts/fetch_churchofmalware.py` | Rebuild every current Church of Malware post/repository from its canonical JSON feed |
| `scripts/rebuild_sources.py` | Rebuild processed content JSON from source markdown |
| `scripts/rebuild_exploitdb_index.py` | Normalize Exploit-DB CSV rows into unique local source-path records with provenance |
| `scripts/rebuild_search_index.py` | Rebuild the complete search index from every committed processed page |
| `scripts/dump_nav_cache.py` | Freeze each source's sidebar tree into `content/nav/` — production has no `sources/` to walk |
| `scripts/enhance_search_index.py` | Add headings and longer excerpts to the search index |
| `scripts/local_fixes.py` | Re-apply corrections to upstream pages after a rebuild overwrites them |
| `scripts/check_fidelity.py` | Prove the build still reproduces committed content before letting it write |
| `scripts/inject_copy_blocks.py` | Build hook for `rebuild_sources.py`; copy buttons are attached client-side, so this is a pass-through |
| `scripts/inject_variable_tokens.py` | Build hook that rewrites upstream example values into `<PLACEHOLDER>` tokens — see the known issue above |

---

## Credits

This project stands entirely on the work of others. Every page traces back to researchers and developers who shared their knowledge publicly.

| Project | Author |
|---|---|
| [BloodHound](https://github.com/SpecterOps/BloodHound) | SpecterOps |
| [The Hacker Recipes](https://github.com/ShutdownRepo/The-Hacker-Recipes) | ShutdownRepo |
| [HackTricks](https://github.com/HackTricks-wiki/hacktricks) | carlospolop |
| [HackTricks Cloud](https://github.com/HackTricks-wiki/hacktricks-cloud) | HackTricks-wiki |
| [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings) | swisskyrepo |
| [InternalAllTheThings](https://github.com/swisskyrepo/InternalAllTheThings) | swisskyrepo |
| [HardwareAllTheThings](https://github.com/swisskyrepo/HardwareAllTheThings) | swisskyrepo |
| [NetExec Wiki](https://github.com/Pennyw0rth/NetExec-Wiki) | Pennyw0rth |
| [GTFOBins](https://github.com/GTFOBins/GTFOBins.github.io) | GTFOBins |
| [LOLBAS](https://github.com/LOLBAS-Project/LOLBAS) | LOLBAS-Project |
| [WADComs](https://github.com/WADComs/WADComs.github.io) | WADComs |
| [Certipy](https://github.com/ly4k/Certipy) | ly4k |
| [bloodyAD](https://github.com/CravateRouge/bloodyAD) | CravateRouge |
| [Impacket](https://github.com/fortra/impacket) | fortra |
| [Rubeus](https://github.com/GhostPack/Rubeus) | GhostPack |
| [Mimikatz](https://github.com/gentilkiwi/mimikatz) | gentilkiwi |
| [Ligolo-ng](https://github.com/nicocha30/ligolo-ng) | nicocha30 |
| [Sliver C2](https://github.com/BishopFox/sliver) | BishopFox |
| [Adaptix C2](https://adaptix-framework.gitbook.io/adaptix-framework/) | Adaptix Framework |
| [goexec](https://github.com/FalconOpsLLC/goexec) | FalconOpsLLC |
| [Metasploit](https://github.com/rapid7/metasploit-framework) | rapid7 |
| [All About Bug Bounty](https://github.com/daffainfo/AllAboutBugBounty) | daffainfo |
| [Church of Malware](https://churchofmalware.org) | 0xXyc et al. |

---

Built by vibe coding with Claude and too much coffee ☕
