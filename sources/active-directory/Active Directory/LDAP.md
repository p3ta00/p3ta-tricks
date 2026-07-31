## LDAP Enumeration

LDAP queries for enumerating Active Directory objects from both Linux and Windows.

---

## From Linux (ldapsearch)

### Syntax Notes

OpenLDAP 2.6 removed the deprecated `-h host` and `-p port` options from every client tool. On Kali 2024+, Debian 12+ and Exegol you get `ldapsearch: unrecognized option` — use `-H <uri>` instead.

```bash
ldapsearch -h <dc-ip> ...              # removed in OpenLDAP 2.6
ldapsearch -H ldap://<dc-ip> ...       # LDAP, port 389
ldapsearch -H ldaps://<dc-ip> ...      # LDAPS, port 636
ldapsearch -H ldap://<dc-ip>:3268 ...  # Global Catalog (forest-wide search)
```

The base DN is a comma-separated list of components, one per DNS label — `fragments.local` is `DC=fragments,DC=local`, not `DC=fragments.local`. Read it off the server instead of guessing.

```bash
ldapsearch -H ldap://<dc-ip> -x -s base -b "" namingContexts defaultNamingContext
```

### Bind Options

```bash
# anonymous simple bind (most DCs refuse this and return operationsError)
ldapsearch -H ldap://<dc-ip> -x -b "DC=<DOMAIN>,DC=LOCAL"

# authenticated simple bind (cleartext password — use ldaps:// or -ZZ)
ldapsearch -H ldap://<dc-ip> -x -D "<username>@<domain>" -w "<password>" -b "DC=<DOMAIN>,DC=LOCAL"

# Kerberos bind using an existing ccache
KRB5CCNAME=<user>.ccache ldapsearch -H ldap://<dc-fqdn> -Y GSSAPI -b "DC=<DOMAIN>,DC=LOCAL"
```

AD caps a search at 1000 entries per response — add paging when enumerating anything large.

```bash
ldapsearch -H ldap://<dc-ip> -x -D "<username>@<domain>" -w "<password>" \
  -b "DC=<DOMAIN>,DC=LOCAL" -E pr=1000/noprompt "(objectClass=user)" sAMAccountName
```

### Enumerate Password Policy

```bash
ldapsearch -H ldap://<dc-ip> -x -b "DC=<DOMAIN>,DC=LOCAL" -s base "(objectClass=*)" minPwdLength pwdHistoryLength lockoutThreshold lockoutDuration maxPwdAge minPwdAge
```

### Enumerate All Users (SamAccountName Only)

```bash
ldapsearch -H ldap://<dc-ip> -x -b "DC=<DOMAIN>,DC=LOCAL" "(&(objectClass=user)(objectCategory=person))" sAMAccountName | grep -i "^sAMAccountName:" | cut -d" " -f2
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
