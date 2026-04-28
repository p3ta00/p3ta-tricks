## General Module Commands

Basic PowerShell and Active Directory module commands for getting oriented in a domain environment.

### Get Loaded PowerShell Modules

Lists all currently loaded PowerShell modules, their version, and available commands.

```powershell
Get-Module
```

### List Commands for a Module

```powershell
Get-Command -Module ActiveDirectory
```

### Get Help on a Cmdlet

```powershell
Get-Help <cmdlet>
```

### Import the Active Directory Module

```powershell
Import-Module ActiveDirectory
```

### RDP to a Target

```bash
xfreerdp /v:<target-ip> /u:<username> /p:<password>
```

### Run a Command as Another User

```cmd
runas /netonly /user:<domain>\<username> powershell
```

---

## AD User Commands

### Create a New AD User

Creates a new user with a secure password and sets additional attributes.

```powershell
New-ADUser -Name "<firstname> <lastname>" -Accountpassword (Read-Host -AsSecureString "Super$ecurePassword!") -Enabled $true -OtherAttributes @{'title'="Analyst";'mail'="f.last@<domain>"}
```

### Remove an AD User

```powershell
Remove-ADUser -Identity <username>
```

### Unlock an AD Account

```powershell
Unlock-ADAccount -Identity <username>
```

### Reset a User's Password

```powershell
Set-ADAccountPassword -Identity '<username>' -Reset -NewPassword (ConvertTo-SecureString -AsPlainText "NewP@ssw0rdReset!" -Force)
```

### Force Password Change at Next Logon

```powershell
Set-ADUser -Identity <username> -ChangePasswordAtLogon $true
```

---

## AD Group & OU Commands

### Create an Organizational Unit

```powershell
New-ADOrganizationalUnit -Name "name" -Path "OU=folder,DC=<domain>,DC=local"
```

### Create a Security Group

```powershell
New-ADGroup -Name "name" -SamAccountName analysts -GroupCategory Security -GroupScope Global -DisplayName "Security Analysts" -Path "CN=Users,DC=<domain>,DC=local" -Description "Members of this group are Security Analysts under the IT OU"
```

### Add Users to a Group

```powershell
Add-ADGroupMember -Identity 'group name' -Members 'user1,user2,user3'
```

---

## GPO Commands

### Copy a GPO

```powershell
Copy-GPO -SourceName "GPO to copy" -TargetName "Name"
```

### Link a GPO to an OU

Links an existing GPO to the specified OU path and enables it.

```powershell
New-GPLink -Name "Security Analysts Control" -Target "ou=Security Analysts,ou=IT,OU=HQ-NYC,OU=Employees,OU=Corp,dc=<domain>,dc=LOCAL" -LinkEnabled Yes
```

### Modify a GPO Link

```powershell
Set-GPLink -Name "Security Analysts Control" -Target "ou=Security Analysts,ou=IT,OU=HQ-NYC,OU=Employees,OU=Corp,dc=<domain>,dc=LOCAL" -LinkEnabled Yes
```

---

## Computer Account Commands

### Add a Computer to the Domain

```powershell
Add-Computer -DomainName '<DOMAIN>' -Credential '<DOMAIN>\<username>' -Restart
```

### Remotely Add a Computer to a Domain

```powershell
Add-Computer -ComputerName 'name' -LocalCredential '.\localuser' -DomainName '<DOMAIN>' -Credential '<DOMAIN>\<username>' -Restart
```

### Check Computer Properties

```powershell
Get-ADComputer -Identity "name" -Properties * | select CN,CanonicalName,IPv4Address
```

---

## Useful LDAP Queries

### List All AD Groups via LDAP Filter

```powershell
Get-ADObject -LDAPFilter '(objectClass=group)' | select cn
```

### List Disabled Users

```powershell
Get-ADUser -LDAPFilter '(userAccountControl:1.2.840.113556.1.4.803:=2)' | select name
```

### Count Users in an OU

```powershell
(Get-ADUser -SearchBase "OU=Employees,DC=<DOMAIN>,DC=LOCAL" -Filter *).count
```

### Find Computers by Hostname Pattern

```powershell
Get-ADComputer -Filter "DNSHostName -like 'SQL*'"
```

### Get All Administrative Groups

```powershell
Get-ADGroup -Filter "adminCount -eq 1" | select Name
```

### Find Admin Users Without Kerberos Pre-Auth

```powershell
Get-ADUser -Filter {adminCount -eq '1' -and DoesNotRequirePreAuth -eq 'True'}
```

### Enumerate UAC Values for Admin Users

```powershell
Get-ADUser -Filter {adminCount -gt 0} -Properties admincount,useraccountcontrol
```

### Get AD Groups via WMI

```powershell
Get-WmiObject -Class win32_group -Filter "Domain='<DOMAIN>'"
```

### Search for All Computers via ADSI

```powershell
([adsisearcher]"(&(objectClass=Computer))").FindAll()
```

### Query Installed Software

```powershell
get-ciminstance win32_product | fl
```

### Check RSAT Tools

```powershell
Get-WindowsCapability -Name RSAT* -Online | Select-Object -Property Name, State
```

### Install All RSAT Tools

```powershell
Get-WindowsCapability -Name RSAT* -Online | Add-WindowsCapability -Online
```
