#!/usr/bin/env python3
"""
For bloodyAD wiki: inserts a clean command-only bash block ABOVE each code block
that mixes shell prompt lines (> cmd) with output lines.
Also normalizes domain/IP placeholders in command lines.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent / 'sources' / 'bloodyad-wiki'

# Replace hardcoded example domains/IPs in command lines
DOMAIN_RE = re.compile(r'\b(?:crash\.lab|bloody\.lab)\b')
HOST_RE   = re.compile(r'\b10\.100\.10\.\d{1,3}\b')
# Also replace 'DC=crash,DC=lab' style DN targets
DN_RE     = re.compile(r"'DC=[a-z]+,DC=[a-z]+'")


def clean_command(line):
    """Strip leading > from prompt lines and normalize placeholders."""
    cmd = line
    if cmd.startswith('> '):
        cmd = cmd[2:]
    cmd = DOMAIN_RE.sub('<domain>', cmd)
    cmd = HOST_RE.sub('<target>', cmd)
    cmd = DN_RE.sub("'DC=<domain>'", cmd)
    return cmd


def process_block(fence_open, body_lines, fence_close):
    """
    Given a code block, if it contains prompt-style command lines (starting with '> '),
    return a clean-command block prepended above the original.
    Otherwise return the block unchanged.
    """
    # Find lines that are commands (start with '> ' or are the sole command)
    prompt_lines = [l for l in body_lines if l.startswith('> ')]

    # Also handle blocks that are ALL commands with no prompt (single-line blocks)
    # We only prepend when there are prompt lines mixed with output
    if not prompt_lines:
        return [fence_open] + body_lines + [fence_close]

    # Extract clean commands
    clean_cmds = [clean_command(l.rstrip('\n').rstrip('\r')) for l in prompt_lines]

    # Build clean command block (bash language tag)
    lang = fence_open.rstrip('\n').rstrip('\r').lstrip('`').lstrip('~').strip()
    if not lang or lang in ('ps1', 'powershell'):
        lang = 'bash'
    fence_char = '```'
    clean_block = (
        [fence_char + lang + '\n'] +
        [cmd + '\n' for cmd in clean_cmds] +
        [fence_char + '\n', '\n']
    )

    return clean_block + [fence_open] + body_lines + [fence_close]


def process_file(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines(keepends=True)
    out = []
    in_fence = False
    fence_marker = ''
    fence_open = ''
    fence_lines = []

    for line in lines:
        stripped = line.rstrip('\n').rstrip('\r')
        if not in_fence:
            m = re.match(r'^(```+|~~~+)', stripped)
            if m:
                in_fence = True
                fence_marker = m.group(1)
                fence_open = line
                fence_lines = []
            else:
                out.append(line)
        else:
            if stripped.startswith(fence_marker) and stripped.strip('`~') == '':
                # Process the complete block
                result = process_block(fence_open, fence_lines, line)
                out.extend(result)
                in_fence = False
                fence_marker = ''
                fence_open = ''
                fence_lines = []
            else:
                fence_lines.append(line)

    # Unclosed fence
    if in_fence and fence_lines:
        result = process_block(fence_open, fence_lines, '')
        out.extend(result)

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
