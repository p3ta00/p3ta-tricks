## Remote Access

### RDP to Target

```bash
xfreerdp /v:<target-ip> /u:<username> /p:<password> /dynamic-resolution
```

## System Information

### OS Info via WMI (PowerShell)

```powershell
Get-WmiObject -Class win32_OperatingSystem
```

### OS Info via WMIC

```cmd
wmic os list brief
```

### Call WMI Object Methods

```powershell
Invoke-WmiMethod
```

## File System

### View All Files and Directories

```cmd
dir c:\ /a
```

### Display Directory Tree

```cmd
tree <directory>
tree c:\ /f | more
```

### View Directory Permissions

```cmd
icacls <directory>
```

### Grant User Full Permissions

```cmd
icacls c:\users /grant <username>:f
```

### Remove User Permissions

```cmd
icacls c:\users /remove <username>
```

## Services

### List Running Services

```powershell
Get-Service
```

## PowerShell

### View Aliases

```powershell
get-alias
```

### Create New Alias

```powershell
New-Alias -Name "Show-Files" Get-ChildItem
```

### View Imported Modules and Commands

```powershell
Get-Module | select Name,ExportedCommands | fl
```

### View Execution Policy

```powershell
Get-ExecutionPolicy -List
```

### Bypass Execution Policy for Current Session

```powershell
Set-ExecutionPolicy Bypass -Scope Process
```

### Get Help for a Command

```cmd
help <command>
```

## User Info

### View Current User SID

```cmd
whoami /user
```

## Registry

### Query Registry Key

```cmd
reg query <key>
```

## Defender

### Check Defender Protection Settings

```powershell
Get-MpComputerStatus
```

## Windows Server Core

### Load Server Configuration Menu

```cmd
sconfig
```
