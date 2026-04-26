#!/usr/bin/env python3
"""Fix certipy-wiki: replace quoted hardcoded values with <varname> placeholders in code blocks."""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent / 'sources' / 'certipy-wiki'

# Patterns for quoted single-quote values in certipy commands
# Order matters — more specific patterns first
RULES = [
    # -u 'user@domain.local' or -u 'USERNAME'
    (re.compile(r"(?<=-u )'[^']+@[^']+'"            ), "'<username>'"),
    (re.compile(r"(?<=-u )'[A-Za-z][A-Za-z0-9._-]*'"), "'<username>'"),
    (re.compile(r"-username '[^']+'"                 ), "-username '<username>'"),

    # -p 'password' (anything in single quotes after -p)
    (re.compile(r"(?<=-p )'[^']*'"                   ), "'<password>'"),

    # -dc-ip 'IP' or -dc-ip IP
    (re.compile(r"(?<=-dc-ip )'[0-9][^']*'"          ), "'<dc-ip>'"),
    (re.compile(r"(?<=-dc-ip )\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"), '<dc-ip>'),
    (re.compile(r"(?<=-ns )'[0-9][^']*'"             ), "'<dc-ip>'"),
    (re.compile(r"(?<=-ns )\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"), '<dc-ip>'),

    # -target 'CA.CORP.LOCAL' (CA hostname)
    (re.compile(r"(?<=-target )'[A-Z][^']+'"         ), "'<target>'"),
    (re.compile(r"(?<=-target )[A-Z][A-Z0-9._-]+\.[A-Z]{2,}"), '<target>'),

    # -ca 'CORP-CA'
    (re.compile(r"(?<=-ca )'[^']+'"                  ), "'<ca>'"),
    (re.compile(r"(?<=-ca )[A-Za-z0-9_-]+-CA\b"      ), '<ca>'),

    # -template 'TemplateName'
    (re.compile(r"(?<=-template )'[^']+'"             ), "'<template>'"),
    (re.compile(r"(?<=-template )[A-Za-z][A-Za-z0-9_-]+(?=\s|\\|$)"), '<template>'),

    # -pfx 'file.pfx' or -pfx file.pfx
    (re.compile(r"(?<=-pfx )'[^']+\.pfx'"            ), "'<pfx>'"),
    (re.compile(r"(?<=-pfx )[A-Za-z0-9._/-]+\.pfx\b" ), '<pfx>'),

    # -upn 'user@domain.local'
    (re.compile(r"(?<=-upn )'[^']+'"                 ), "'<upn>'"),
    (re.compile(r"(?<=-upn )[A-Za-z][^'@\s]+@[^\s']+"   ), '<upn>'),

    # -domain 'CORP.LOCAL' or -domain corp.local
    (re.compile(r"(?<=-domain )'[^']+'"              ), "'<domain>'"),
    (re.compile(r"(?<=-domain )[A-Za-z][a-z0-9.-]+\.[a-z]{2,}"), '<domain>'),

    # -key-size value (not a var — skip)
    # -sid 'S-1-5-...'
    (re.compile(r"(?<=-sid )'S-[0-9-]+'"             ), "'<sid>'"),
    (re.compile(r"(?<=-sid )S-[0-9-]+\b"             ), '<sid>'),

    # -username USERNAME (bare)
    (re.compile(r"'USERNAME'"                         ), "'<username>'"),
    (re.compile(r"'PASSWORD'"                         ), "'<password>'"),
    (re.compile(r"'DC_IP'"                            ), "'<dc-ip>'"),
]


def process_code_block(lines):
    result = []
    for line in lines:
        new_line = line
        # Only apply to lines that look like certipy commands
        stripped = line.lstrip()
        if any(stripped.startswith(p) for p in ('certipy', 'python', '-u ', '-p ', '>')):
            for pattern, replacement in RULES:
                new_line = pattern.sub(replacement, new_line)
        result.append(new_line)
    return result


def process_file(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines(keepends=True)
    out = []
    in_fence = False
    fence_marker = ''
    fence_lines = []

    for line in lines:
        stripped = line.rstrip('\n').rstrip('\r')
        if not in_fence:
            m = re.match(r'^(\s*)(```+|~~~+)', stripped)
            if m:
                in_fence = True
                fence_marker = m.group(2)
                fence_lines = [line]
            else:
                out.append(line)
        else:
            close_stripped = stripped.lstrip()
            if close_stripped.startswith(fence_marker) and close_stripped.strip('`~') == '':
                processed = process_code_block(fence_lines[1:])
                out.append(fence_lines[0])
                out.extend(processed)
                out.append(line)
                in_fence = False
                fence_lines = []
            else:
                fence_lines.append(line)

    if in_fence and fence_lines:
        processed = process_code_block(fence_lines[1:])
        out.append(fence_lines[0])
        out.extend(processed)

    new_text = ''.join(out)
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
        return True
    return False


if __name__ == '__main__':
    files = sorted(ROOT.rglob('*.md'))
    changed = 0
    for f in files:
        if process_file(f):
            print(f'  CHANGED: {f.name}')
            changed += 1
    print(f'{changed}/{len(files)} files modified')
