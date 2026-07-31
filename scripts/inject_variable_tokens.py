#!/usr/bin/env python3
"""Normalise upstream example values into the site's fill-in placeholders.

Applied by rebuild_sources.py to the markdown of every source in _VAR_SOURCES,
before rendering. The front-end (static/js/app.js) finds the resulting
`<PLACEHOLDER>` tokens in code blocks and lets you fill each one once per
session, so a command copied off any page already points at your target.

Substitution is whole-token (whitespace-delimited): `username` becomes
`<USERNAME>` but `username1` is left alone unless it is in the table itself.

Only fenced code blocks are rewritten. Prose is left exactly as upstream wrote
it -- "all user objects with the adminCount attribute" must not turn into
"all <USERNAME> objects".

INCOMPLETE -- DO NOT TRUST FOR A FULL REBUILD
---------------------------------------------
The original of this file was lost with the CachyOS box (scripts/ is gitignored
and it was never committed). This is a reconstruction, recovered by diffing the
committed content -- which had the real transform applied -- against a rebuild
that did not.

It is close but not equivalent. Measured against the criterion "a page whose
upstream markdown did not change must rebuild byte-identically", it reproduces
about 65% of the corpus; NetExec upstream changed 2 files since the last pull
yet 54 of its pages come out different. Those 52 extra are this file getting the
substitution wrong, and a full rebuild would ship them.

`update.sh` therefore runs scripts/check_fidelity.py before letting a rebuild
touch content/, and refuses when churn is implausibly high. Improve the TABLE
and the rules below until check_fidelity passes, then the weekly update runs
unattended again.
"""
import re

FENCE_RE = re.compile(r"^```[^\n]*\n.*?^```", re.M | re.S)

# literal -> placeholder, recovered from the corpus
TABLE = {
    "$PASSWORD": "<PASSWORD>",
    "$USER": "<USERNAME>",
    "$USERNAME": "<USERNAME>",
    "$password": "<PASSWORD>",
    "$user": "<USERNAME>",
    "'13b29964cc2480b4ef454c59562e675c'": "<HASH>",
    "'P@ssw0rd'": "<PASSWORD>",
    "'PASSWORDHERE'": "<PASSWORD>",
    "'Password123!'": "<password>",
    "'aad3b435b51404eeaad3b435b51404ee:13b29964cc2480b4ef454c59562e675c'": "<HASH>",
    "'pass'": "<PASSWORD>",
    "'password'": "<PASSWORD>",
    "'totoTOTOtoto1234*'": "<password>",
    "/path/to/users.txt": "<USERFILE>",
    "Administrator": "<USERNAME>",
    "FightP3aceAndHonor!": "<PASSWORD>",
    "Password512": "<password>",
    "Password512!": "<password>",
    "Summer18": "<PASSWORD>",
    "USER": "<USERNAME>",
    "UserNAme": "<USERNAME>",
    "UserName": "<USERNAME>",
    "admin": "<username>",
    "administrator": "<USERNAME>",
    "alice": "<USERNAME>",
    "bloodyAdmin": "<username>",
    "domain": "<DOMAIN>",
    "eddard.stark": "<USERNAME>",
    "harry": "<USERNAME>",
    "james": "<USERNAME>",
    "john.doe": "<username>",
    "pass": "<PASSWORD>",
    "password": "<PASSWORD>",
    "password.txt": "<PASSFILE>",
    "password1": "<PASSWORD>",
    "passwords.txt": "<PASSFILE>",
    "user": "<USERNAME>",
    "user.txt": "<USERFILE>",
    "username": "<USERNAME>",
    "usernames.txt": "<USERFILE>",
    "users.txt": "<USERFILE>",
    "users_file.txt": "<USERFILE>",
    "~/file_containing_passwords": "<PASSFILE>",
    "~/file_containing_usernames": "<USERFILE>"
}

# every example address becomes the same target placeholder
CIDR_RE = re.compile(r"(?<!\S)\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}(?!\S)")
IPV4_RE = re.compile(r"(?<!\S)\d{1,3}(?:\.\d{1,3}){3}(?!\S)")

# longest first so `password1` wins over `password`
_LITERALS = sorted(TABLE, key=len, reverse=True)
_TABLE_RE = re.compile(
    r"(?<!\S)(" + "|".join(re.escape(t) for t in _LITERALS) + r")(?!\S)"
) if _LITERALS else None


def _rewrite(block: str) -> str:
    block = CIDR_RE.sub("<CIDR>", block)
    block = IPV4_RE.sub("<TARGET>", block)
    if _TABLE_RE:
        block = _TABLE_RE.sub(lambda m: TABLE[m.group(1)], block)
    return block


def inject_variable_tokens(text: str) -> str:
    return FENCE_RE.sub(lambda m: _rewrite(m.group(0)), text)


if __name__ == "__main__":
    import sys
    sys.stdout.write(inject_variable_tokens(sys.stdin.read()))
