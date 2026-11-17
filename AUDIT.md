# Online Release Audit

Audit timestamp: **2026-11-17T03:30:57Z**

This audit covers the online `p3ta-tricks` release independently from the air-gapped repository. It validates acquisition provenance, generated content, navigation, search, recoverable media, application routes, and representative browser rendering.

## Current corpus

- **4,975** searchable documentation pages across **31 indexed page sources**.
- **36** source families exposed by the application, including special tools such as Exploit-DB and CyberChef.
- **1,519** committed source-relative documentation assets.
- **1,668** committed recovered third-party images.
- **223** current Church of Malware pages: 20 scripture posts and 203 public repositories.

## Exploit-DB

The official `files_exploits.csv` contains **47,182 raw rows**. Those rows are not 47,182 distinct local files: upstream repeats metadata rows for some source paths. The application therefore exposes **46,710 unique locally addressable source-path records**, merging CVEs and tags deterministically.

- Upstream commit: `70bbef3f18b835b0d8bacb978f2bc7b751a7cec9`
- Database revision: **2026-11-12**
- Newest record: **EDB-ID 52705**
- Duplicate rows merged: **472** across **461** source-path groups
- Missing source files in the verified maintainer checkout: **0**
- Online code route for EDB-ID 52705: **HTTP 200**, 5,727-byte response

## Source freshness

Official remote heads were fetched and compared immediately before release:

- HackTricks: `c457a24e9012eca0a33562a587827f700182c799`
- HackTricks Cloud: `81d5fcd59b54f03a5786abd94fa6037af462da62`
- Sliver: `aa787bf0e1c4a19a340c38227ebf5e0715c69d56`
- Exploit-DB: `70bbef3f18b835b0d8bacb978f2bc7b751a7cec9`
- Church of Malware canonical inventory: `sha256:c176c40510c972b322b58c7b4ae2110183ca239efc615da07e07e530aa7d66ce`
- Adaptix public export: `sha256:2655c30726f89b517705ebb53ead3233dcf87b1e1526366771974318574ba28e`

All other Git-backed inputs in `content/source-lock.json` were fetched and matched their official remote branch heads.

## Generated-data corrections

The audit found and corrected silent stale-output retention in the previous rebuild pipeline. A source rebuild now deletes that source family's old generated JSON before writing current output. Three genuine HackTricks source-path collisions are retained through stable `--standalone` disambiguation instead of silent overwrite.

Dedicated fail-closed transforms now cover:

- the complete Exploit-DB CSV normalization;
- the canonical Church of Malware JSON feed;
- the complete search index reconstructed from committed processed pages;
- recoverable third-party image localization, with blocked/deleted decorative image tags removed rather than left broken.

The later ghost-content cleanup removed the obsolete private HTB/HTB Academy
import pipeline, its 120 generated pages, navigation cache, source registration,
homepage credit, dedicated CSS, hidden-source filters, and its final unreferenced
named asset. Legitimate upstream documentation citations remain part of their
respective public source pages.

## Full application crawl

- Navigation URLs: **5,305**
- Application URLs crawled: **5,501**
- Internal links checked: **5,054**
- Rendered local assets checked: **514**
- Broken/non-200 references: **0**
- Automatically loaded remote assets: **0**
- Placeholder pages: **0**
- Empty/dead content pages: **0**
- Duplicate search URLs: **0**

## Runtime and visual checks

The real Flask application was started locally and tested through both its HTTP/API routes and headless Microsoft Edge. The homepage, Church of Malware source page, and fully loaded Exploit-DB table rendered without visible broken images, placeholders, empty states, or layout regressions. The Exploit-DB table visibly reported **46,710 / 46,710 exploits** and EDB-ID **52705** as the newest row.

Machine-readable evidence is in [`AUDIT_REPORT.json`](AUDIT_REPORT.json).
