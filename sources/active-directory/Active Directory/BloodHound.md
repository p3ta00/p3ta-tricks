## BloodHound Collection

BloodHound maps attack paths through Active Directory by ingesting data about users, groups, computers, ACLs, and trusts. Collect data with SharpHound or bloodhound-python, then import into the BloodHound GUI.

---

## SharpHound (Windows)

### C# Ingestor

Runs all collection methods and outputs a zip file ready for BloodHound import.

```powershell
.\SharpHound.exe -c all --zipfilename <domain>_bloodhound
```

### PowerShell Ingestor

```powershell
Invoke-BloodHound -CollectionMethod all -ZipFileName <domain>_bloodhound
```

---

## bloodhound-python (Linux)

Runs the Python BloodHound collector remotely. Requires valid domain credentials.

```bash
bloodhound-python -dc <dc-hostname> -gc <gc-hostname> -d <domain> -c All -u <username>
sudo bloodhound-python -u '<username>' -p '<password>' -ns <dc-ip> -d <domain> -c all
```

### Cross-Forest Collection

```bash
bloodhound-python -d <DOMAIN> -dc <dc-hostname> -c All -u <username> -p <password>
```

---

## File Transfer for Collection

### RDP with Drive Redirection

Mount a local directory in the RDP session for easy file transfer.

```bash
xfreerdp /v:<target-ip> /u:<username> /drive:data,/tmp
```

### Compress JSON Files for Import

After running bloodhound-python, compress the output files for import.

```bash
zip -r domain_bh.zip *.json
```

---

## Key BloodHound Queries

Run these in the BloodHound GUI (Raw Query tab) to find attack paths:

### Shortest Path to Domain Admins

Pre-built query in the Analysis tab.

### Find All Kerberoastable Users

Pre-built query in the Analysis tab.

### Find All AS-REP Roastable Users

Pre-built query in the Analysis tab.

### Find Principals with DCSync Rights

Pre-built query in the Analysis tab.

### Find Users with Local Admin Anywhere

Pre-built query in the Analysis tab.

### Cypher - WriteSPN Rights (for SPN Jacking)

```cypher
MATCH p=(n:User)-[r1:WriteSPN*1..]->(c:Computer) RETURN p
```
