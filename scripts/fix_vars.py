#!/usr/bin/env python3
"""
Converts hardcoded placeholder values in markdown source files to <varname> syntax
for the variable substitution system.

Run: python3 scripts/fix_vars.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent / 'sources'

# ──────────────────────────────────────────────────────────────────
# Generic IP replacement: matches common private/example IPv4 addresses
# in command-line contexts. Only replaces on lines that look like commands
# (start with a tool name, not output).
# ──────────────────────────────────────────────────────────────────
COMMAND_PREFIXES = (
    'nxc ', 'netexec ', 'crackmapexec ', 'cme ',
    'bloodyad ', 'bloodyAD ', 'python3 bloodyad',
    'certipy ', 'certipy-ad ',
    'impacket', 'secretsdump', 'getTGT', 'getst', 'psexec', 'wmiexec', 'smbexec',
    'evil-winrm ', 'ssh ', 'scp ', 'curl ', 'wget ',
)

PLACEHOLDER_IP_RE = re.compile(
    r'\b(?:'
    r'10\.10\.10\.\d{1,3}|'          # 10.10.10.x
    r'10\.10\.1[0-9]\.\d{1,3}|'      # 10.10.1x.x (HTB subnets)
    r'192\.168\.\d{1,3}\.\d{1,3}|'   # 192.168.x.x
    r'172\.16\.\d{1,3}\.\d{1,3}|'    # 172.16.x.x
    r'10\.0\.\d{1,3}\.\d{1,3}'       # 10.0.x.x
    r')(?:/\d{1,2})?'                 # optional CIDR
)

# ──────────────────────────────────────────────────────────────────
# Per-source rules: list of (pattern, replacement) applied only within
# fenced code blocks. Patterns are applied in order.
# ──────────────────────────────────────────────────────────────────

# Rules applied to all netexec-wiki files (within code fences)
NXC_RULES = [
    # -u 'user' / -u user / -u UserNAme
    (re.compile(r"(?<=-u )'user'"),          '<username>'),
    (re.compile(r"(?<=-u )'username'"),       '<username>'),
    (re.compile(r"(?<=-u )UserNAme\b"),       '<username>'),
    (re.compile(r"(?<=-u )alice\b"),          '<username>'),
    (re.compile(r"(?<=-u )harry\b"),          '<username>'),
    # standalone bare 'user' as the -u value (no quotes needed after)
    # only when directly after -u and not already <username>
    (re.compile(r"(?<=-u )user(?!\w)"),       '<username>'),

    # -p 'pass' / -p pass / -p 'password' / -p 'PASSWORDHERE'
    (re.compile(r"(?<=-p )'pass'"),           '<password>'),
    (re.compile(r"(?<=-p )pass(?!\w)"),       '<password>'),
    (re.compile(r"(?<=-p )'password'"),       '<password>'),
    (re.compile(r"(?<=-p )password(?!\w)"),   '<password>'),
    (re.compile(r"(?<=-p )'PASSWORDHERE'"),   '<password>'),
    (re.compile(r"(?<=-p )PASSWORDHERE"),     '<password>'),
    # October2022! style — skip (it's a demonstration of special chars)

    # -H 'LM:NT' / -H 'NTHASH'
    (re.compile(r"(?<=-H )'LM:NT'"),          '<ntlm-hash>'),
    (re.compile(r"(?<=-H )LM:NT\b"),          '<ntlm-hash>'),
    (re.compile(r"(?<=-H )'NTHASH'"),         '<nt-hash>'),
    (re.compile(r"(?<=-H )NTHASH\b"),         '<nt-hash>'),
    # -H 'aad3b435b51404ee...' (LM:NT full hash demo)
    (re.compile(r"(?<=-H )'aad3b435b51404eeaad3b435b51404ee:[0-9a-f]{32}'"), '<ntlm-hash>'),
    # -H '13b29964cc2480b4ef454c59562e675c' (NT hash demo)
    (re.compile(r"(?<=-H )'[0-9a-f]{32}'"),   '<nt-hash>'),
    (re.compile(r"(?<=-H )[0-9a-f]{32}\b"),   '<nt-hash>'),
]

# Rules applied specifically to lines that start with a known tool command
NXC_IP_RULE = True  # replace IPs on nxc command lines

# ──────────────────────────────────────────────────────────────────
# BloodyAD rules
# ──────────────────────────────────────────────────────────────────
BLOODY_RULES = [
    (re.compile(r"(?<=-u )'?[A-Za-z][A-Za-z0-9_.-]*'?(?=\s)"), '<username>'),
    (re.compile(r"(?<=-p )'?[A-Za-z][A-Za-z0-9!@#$%^&*_.-]*'?(?=\s|$)"), '<password>'),
    (re.compile(r"(?<=--dc )[A-Za-z0-9.-]+\b"), '<dc-ip>'),
    (re.compile(r"(?<=--domain )[A-Za-z0-9.-]+\b"), '<domain>'),
]

# ──────────────────────────────────────────────────────────────────
# Certipy rules
# ──────────────────────────────────────────────────────────────────
CERTIPY_RULES = [
    (re.compile(r"(?<=-username )[A-Za-z][A-Za-z0-9._-]*(?=\s|$)"), '<username>'),
    (re.compile(r"(?<=-u )[A-Za-z][A-Za-z0-9._-]*(?=\s|$)"), '<username>'),
    (re.compile(r"(?<=-password )[A-Za-z0-9!@#$%^&*_.-]+(?=\s|$)"), '<password>'),
    (re.compile(r"(?<=-p )[A-Za-z0-9!@#$%^&*_.-]+(?=\s|$)"), '<password>'),
    (re.compile(r"(?<=-dc-ip )\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"), '<dc-ip>'),
    (re.compile(r"(?<=-ca )[A-Za-z0-9._-]+-CA\b"), '<ca>'),
    (re.compile(r"(?<=-template )[A-Za-z][A-Za-z0-9_-]*(?=\s|$)"), '<template>'),
    (re.compile(r"(?<=-domain )[a-z][a-z0-9.-]+\.[a-z]{2,}"), '<domain>'),
]

# ──────────────────────────────────────────────────────────────────
# Processor
# ──────────────────────────────────────────────────────────────────

def is_command_line(line):
    stripped = line.lstrip()
    return any(stripped.startswith(p) for p in COMMAND_PREFIXES)


def apply_rules_to_line(line, rules, replace_ips=False):
    """Apply substitution rules to a single line."""
    result = line
    for pattern, replacement in rules:
        result = pattern.sub(replacement, result)
    if replace_ips and is_command_line(result):
        result = PLACEHOLDER_IP_RE.sub('<target>', result)
    return result


def process_code_block(lines, rules, replace_ips=False):
    """Apply rules to lines inside a fenced code block."""
    return [apply_rules_to_line(l, rules, replace_ips) for l in lines]


def process_file(path, rules, replace_ips=False):
    """Process a single markdown file, applying rules only inside code fences."""
    text = path.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines(keepends=True)
    out = []
    in_fence = False
    fence_marker = ''
    fence_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip('\n').rstrip('\r')

        if not in_fence:
            # Check for opening fence
            m = re.match(r'^(```+|~~~+)', stripped)
            if m:
                in_fence = True
                fence_marker = m.group(1)
                fence_lines = [line]
            else:
                out.append(line)
        else:
            # Check for closing fence
            if stripped.startswith(fence_marker) and stripped.strip('`~') == '':
                # Process accumulated fence lines
                processed = process_code_block(fence_lines[1:], rules, replace_ips)
                out.append(fence_lines[0])
                out.extend(processed)
                out.append(line)
                in_fence = False
                fence_marker = ''
                fence_lines = []
            else:
                fence_lines.append(line)
        i += 1

    # Unclosed fence — flush as-is
    if in_fence and fence_lines:
        processed = process_code_block(fence_lines[1:], rules, replace_ips)
        out.append(fence_lines[0])
        out.extend(processed)

    new_text = ''.join(out)
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
        return True
    return False


def process_directory(source_id, rules, replace_ips=False):
    source_dir = ROOT / source_id
    if not source_dir.exists():
        print(f'  SKIP: {source_dir} does not exist')
        return
    files = sorted(source_dir.rglob('*.md'))
    changed = 0
    for f in files:
        if process_file(f, rules, replace_ips):
            print(f'  CHANGED: {f.relative_to(ROOT)}')
            changed += 1
    print(f'  {changed}/{len(files)} files modified in {source_id}')


if __name__ == '__main__':
    print('=== netexec-wiki ===')
    process_directory('netexec-wiki', NXC_RULES, replace_ips=True)

    print('=== bloodyad-wiki ===')
    process_directory('bloodyad-wiki', BLOODY_RULES, replace_ips=True)

    print('=== certipy-wiki ===')
    process_directory('certipy-wiki', CERTIPY_RULES, replace_ips=True)
