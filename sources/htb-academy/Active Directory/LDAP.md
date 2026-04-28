## LDAP Enumeration

LDAP queries for enumerating Active Directory objects from both Linux and Windows.

---

## From Linux (ldapsearch)

### Enumerate Password Policy

```bash
ldapsearch -h <dc-ip> -x -b "DC=<DOMAIN>,DC=LOCAL" -s sub "*" | grep -m 1 -B 10 pwdHistoryLength
```

### Enumerate All Users (SamAccountName Only)

```bash
ldapsearch -h <dc-ip> -x -b "DC=<DOMAIN>,DC=LOCAL" -s sub "(&(objectclass=user))" | grep sAMAccountName: | cut -f2 -d" "
```

---

## From Windows (ADSI / AD Module)

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

### Search for All Computers (ADSI)

```powershell
([adsisearcher]"(&(objectClass=Computer))").FindAll()
```

---

## windapsearch (Python)

Anonymous enumeration of domain users.

```bash
./windapsearch.py --dc-ip <dc-ip> -u "" -U
```

Authenticated enumeration - Domain Admins:

```bash
python3 windapsearch.py --dc-ip <dc-ip> -u <domain>\<username> -p <password> --da
```

Recursive privileged user search:

```bash
python3 windapsearch.py --dc-ip <dc-ip> -u <domain>\<username> -p <password> -PU
```

---

## adidnsdump

Resolve all DNS records in a zone over LDAP. Useful for mapping the internal network from unauthenticated or limited-privilege positions.

```bash
adidnsdump -u <domain>\\<username> ldap://<dc-ip>
adidnsdump -u <domain>\\<username> ldap://<dc-ip> -r
```
