#!/usr/bin/env python3
"""
p3ta-tricks MCP maintenance server.

Manages two separate deployment modes:
  - ONLINE (port 5000): wiki only, GitHub links live, requires internet
  - OFFLINE (port 5001): wiki + local tools, GitHub links intercepted, fully offline

Tools:
  Wiki maintenance:  check_updates, pull_updates, rebuild_index, restart_server,
                     source_status, list_sources, update_all
  Offline tool mgmt: watt_tool_status, install_missing_tools, update_watt_tools,
                     check_tool_updates, compile_tool, compile_all_tools,
                     sync_releases, watt_diff, sync_binaries

Usage: python3 mcp_server.py
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

ROOT         = Path(__file__).parent.resolve()
WATT_ROOT    = ROOT.parent / "p3ta-tricks-offline"  # was p3ta-tricks-watt
TOOLS_DIR    = WATT_ROOT / "tools"
BINARIES_DIR = ROOT / "binaries"  # served on both online and offline modes
SOURCES      = ROOT / "sources"
BUILD_SCRIPT = ROOT / "scripts" / "build.py"

SOURCE_REGISTRY = {
    "hacker-recipes":   {"dir": "hacker-recipes",      "git": True,  "label": "Hacker Recipes"},
    "hacktricks":       {"dir": "hacktricks",           "git": True,  "label": "HackTricks"},
    "hacktricks-cloud": {"dir": "hacktricks-cloud",     "git": True,  "label": "HackTricks Cloud"},
    "netexec":          {"dir": "netexec-wiki",          "git": True,  "label": "NetExec"},
    "gtfobins":         {"dir": "gtfobins",              "git": True,  "label": "GTFOBins"},
    "lolbas":           {"dir": "lolbas",                "git": True,  "label": "LOLBAS"},
    "bloodyad":         {"dir": "bloodyad-wiki",         "git": True,  "label": "bloodyAD"},
    "certipy":          {"dir": "certipy-wiki",          "git": True,  "label": "Certipy"},
    "ligolo-ng":        {"dir": "ligolo-ng-wiki",        "git": True,  "label": "Ligolo-ng"},
    "patt":             {"dir": "payloadsallthethings",  "git": True,  "label": "PATT"},
    "hardware-att":     {"dir": "hardwareallthethings",  "git": True,  "label": "HardwareATT"},
    "internal-att":     {"dir": "internalallthethings",  "git": True,  "label": "InternalATT"},
    "goexec":           {"dir": "goexec",                "git": True,  "label": "GoExec"},
    "osai-research":    {"dir": "osai-research",         "git": True,  "label": "OSAI Research"},
    "sliver":           {"dir": "sliver-docs",           "git": False, "label": "Sliver (plain)"},
    "impacket":         {"dir": "impacket",              "git": False, "label": "Impacket (plain)"},
    "rubeus":           {"dir": "rubeus",                "git": False, "label": "Rubeus (plain)"},
    "mimikatz":         {"dir": "mimikatz",              "git": False, "label": "Mimikatz (plain)"},
    "bloodhound":       {"dir": "bloodhound",            "git": False, "label": "BloodHound (plain)"},
    "msfvenom":         {"dir": "msfvenom",              "git": False, "label": "msfvenom (plain)"},
}

# GitHub slug → local dir in TOOLS_DIR
# Aliases (multiple slugs → same dir) are fine; only unique dirs are acted on.
TOOL_REGISTRY = {
    # ── Windows Privilege Escalation ─────────────────────────────────────────
    "BeichenDream/GodPotato":                    "GodPotato",
    "itm4n/PrintSpoofer":                        "PrintSpoofer",
    "itm4n/PrivescCheck":                        "PrivescCheck",
    "GhostPack/Seatbelt":                        "Seatbelt",
    "rasta-mouse/Watson":                        "Watson",
    "carlospolop/PEASS-ng":                      "PEASS-ng",
    "peass-ng/PEASS-ng":                         "PEASS-ng",
    "ohpe/juicy-potato":                         "juicy-potato",
    "antonioCoco/RoguePotato":                   "RoguePotato",
    "CCob/SweetPotato":                          "SweetPotato",
    "GhostPack/SharpUp":                         "SharpUp",
    "gtworek/Priv2Admin":                        "Priv2Admin",
    "SecWiki/windows-kernel-exploits":           "windows-kernel-exploits",
    "breenmachine/RottenPotatoNG":               "RottenPotatoNG",
    # ── GhostPack / C# ───────────────────────────────────────────────────────
    "GhostPack/Rubeus":                          "Rubeus",
    "GhostPack/Certify":                         "Certify",
    "GhostPack/SharpDPAPI":                      "SharpDPAPI",
    "GhostPack/SafetyKatz":                      "SafetyKatz",
    "Flangvik/SharpCollection":                  "SharpCollection",
    "tevora-threat/SharpView":                   "SharpView",
    "0xthirteen/SharpMove":                      "SharpMove",
    # ── ADCS / Certificates ───────────────────────────────────────────────────
    "ly4k/Certipy":                              "Certipy",
    "AlmondOffSec/PassTheCert":                  "PassTheCert",
    "jamarir/Invoke-PassTheCert":                "PassTheCert",
    "bats3c/ADCSPwn":                            "ADCSPwn",
    "GhostPack/ForgeCert":                       "ForgeCert",
    # ── Kerberos ─────────────────────────────────────────────────────────────
    "dirkjanm/krbrelayx":                        "krbrelayx",
    "dirkjanm/PKINITtools":                      "PKINITtools",
    "ShutdownRepo/targetedKerberoast":           "targetedKerberoast",
    "ropnop/kerbrute":                           "kerbrute",
    "gentilkiwi/kekeo":                          "kekeo",
    "TarlogicSecurity/tickey":                   "tickey",
    "SecuraBV/Timeroast":                        "Timeroast",
    # ── Coercion / NTLM Relay ────────────────────────────────────────────────
    "topotam/PetitPotam":                        "PetitPotam",
    "p0dalirius/Coercer":                        "Coercer",
    "Wh04m1001/DFSCoerce":                       "DFSCoerce",
    "ShutdownRepo/ShadowCoerce":                 "ShadowCoerce",
    "lgandx/Responder":                          "Responder",
    "SpiderLabs/Responder":                      "Responder",
    "dirkjanm/mitm6":                            "mitm6",
    "Kevin-Robertson/Inveigh":                   "Inveigh",
    # ── Shadow Credentials ────────────────────────────────────────────────────
    "eladshamir/Whisker":                        "Whisker",
    "ShutdownRepo/pywhisker":                    "pywhisker",
    # ── AD Enumeration ────────────────────────────────────────────────────────
    "dirkjanm/BloodHound.py":                    "BloodHound.py",
    "CravateRouge/bloodyAD":                     "bloodyAD",
    "PowerShellMafia/PowerSploit":               "PowerSploit",
    "FuzzySecurity/StandIn":                     "StandIn",
    "dirkjanm/ldapdomaindump":                   "ldapdomaindump",
    "dirkjanm/ROADtools":                        "ROADtools",
    "Kevin-Robertson/Powermad":                  "Powermad",
    "franc-pentest/ldeep":                       "ldeep",
    "SnaffCon/Snaffler":                         "Snaffler",
    "EmpireProject/Empire":                      "Empire",
    # ── gMSA ──────────────────────────────────────────────────────────────────
    "Semperis/GoldenGMSA":                       "GoldenGMSA",
    "felixbillieres/pyGoldenGMSA":               "pyGoldenGMSA",
    # ── SCCM ──────────────────────────────────────────────────────────────────
    "subat0mik/Misconfiguration-Manager":        "Misconfiguration-Manager",
    "Mayyhem/SharpSCCM":                         "SharpSCCM",
    "garrettfoster13/sccmhunter":                "sccmhunter",
    # ── LSASS / Credential Extraction ────────────────────────────────────────
    "Hackndo/lsassy":                            "lsassy",
    "fortra/nanodump":                           "nanodump",
    "AlessandroZ/LaZagne":                       "LaZagne",
    "login-securite/DonPAPI":                    "DonPAPI",
    "skelsec/pypykatz":                          "pypykatz",
    "lgandx/PCredz":                             "PCredz",
    # ── Mimikatz ─────────────────────────────────────────────────────────────
    "gentilkiwi/mimikatz":                       "mimikatz-tool",
    # ── MSSQL ─────────────────────────────────────────────────────────────────
    "NetSPI/PowerUpSQL":                         "PowerUpSQL",
    "ScorpionesLabs/MSSqlPwner":                 "MSSqlPwner",
    # ── PowerShell Post-Ex ────────────────────────────────────────────────────
    "samratashok/nishang":                       "nishang",
    # ── Tunneling ─────────────────────────────────────────────────────────────
    "jpillora/chisel":                           "chisel",
    "Fahrj/reverse-ssh":                         "reverse-ssh",
    # ── Linux ─────────────────────────────────────────────────────────────────
    "DominicBreuker/pspy":                       "pspy",
    "diego-treitos/linux-smart-enumeration":     "linux-smart-enumeration",
    "nongiach/sudo_inject":                      "sudo_inject",
    # ── Java Deserialization ──────────────────────────────────────────────────
    "frohoff/ysoserial":                         "ysoserial-java",
    # ── Web Exploitation ──────────────────────────────────────────────────────
    "pwntester/ysoserial.net":                   "ysoserial.net",
    "epinna/tplmap":                             "tplmap",
    "tarunkant/Gopherus":                        "Gopherus",
    "ticarpi/jwt_tool":                          "jwt_tool",
    # ── Web Recon ─────────────────────────────────────────────────────────────
    "assetnote/blind-ssrf-chains":              "blind-ssrf-chains",
    "s0md3v/Arjun":                             "Arjun",
    # ── VoIP ──────────────────────────────────────────────────────────────────
    "Pepelux/sippts":                           "sippts",
    # ── Java RMI ──────────────────────────────────────────────────────────────
    "qtc-de/remote-method-guesser":             "remote-method-guesser",
    # ── Azure / Cloud ─────────────────────────────────────────────────────────
    "NetSPI/MicroBurst":                         "MicroBurst",
    "RhinoSecurityLabs/pacu":                    "pacu",
    # ── BloodHound ────────────────────────────────────────────────────────────
    "BloodHoundAD/BloodHound":                   "BloodHound.py",
    # ── .NET RE ───────────────────────────────────────────────────────────────
    "dnspy/dnspy":                               "dnspy",
    # ── NetExec ───────────────────────────────────────────────────────────────
    "Pennyw0rth/NetExec":                        "NetExec",
    # ── Misc ──────────────────────────────────────────────────────────────────
    "Hackndo/pyGPOAbuse":                        "pyGPOAbuse",
    "n00py/LAPSDumper":                          "LAPSDumper",
    "layer8secure/SilentHound":                  "SilentHound",
    "t3l3machus/Villain":                        "Villain",
    "sensepost/objection":                       "objection",
    "bettercap/bettercap":                       "bettercap",
    "SecureAuthCorp/impacket":                   "impacket-src",
    "fortra/impacket":                           "impacket-src",
    "CVE-2021-1675/cube0x0":                     "CVE-2021-1675",
}

# Tools that publish GitHub release binaries — slug → [(asset_url_or_pattern, dest_filename)]
# These are re-downloaded by sync_releases rather than compiled from source.
RELEASE_REGISTRY = {
    "ropnop/kerbrute":        [
        ("https://github.com/ropnop/kerbrute/releases/download/v1.0.3/kerbrute_linux_amd64", "kerbrute_linux_amd64"),
    ],
    "jpillora/chisel":        [
        ("https://github.com/jpillora/chisel/releases/download/v1.11.5/chisel_1.11.5_linux_amd64.gz", "chisel_linux_amd64.gz"),
    ],
    "DominicBreuker/pspy":    [
        ("https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy64", "pspy64"),
        ("https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy32", "pspy32"),
    ],
    "Fahrj/reverse-ssh":      [
        ("https://github.com/Fahrj/reverse-ssh/releases/download/v1.2.0/reverse-sshx64",     "reverse-sshx64"),
        ("https://github.com/Fahrj/reverse-ssh/releases/download/v1.2.0/reverse-sshx86",     "reverse-sshx86"),
        ("https://github.com/Fahrj/reverse-ssh/releases/download/v1.2.0/reverse-sshx64.exe", "reverse-sshx64.exe"),
        ("https://github.com/Fahrj/reverse-ssh/releases/download/v1.2.0/reverse-sshx86.exe", "reverse-sshx86.exe"),
    ],
    "bettercap/bettercap":    [
        ("https://github.com/bettercap/bettercap/releases/download/v2.41.5/bettercap_linux_amd64.zip", "bettercap_linux_amd64.zip"),
    ],
    "gentilkiwi/mimikatz":    [
        ("https://github.com/gentilkiwi/mimikatz/releases/download/2.2.0-20220919/mimikatz_trunk.zip", "mimikatz_trunk.zip"),
    ],
    "gentilkiwi/kekeo":       [
        ("https://github.com/gentilkiwi/kekeo/releases/download/2.2.0-20211214/kekeo.zip", "kekeo.zip"),
    ],
    "itm4n/PrintSpoofer":     [
        ("https://github.com/itm4n/PrintSpoofer/releases/download/v1.0/PrintSpoofer32.exe", "PrintSpoofer32.exe"),
        ("https://github.com/itm4n/PrintSpoofer/releases/download/v1.0/PrintSpoofer64.exe", "PrintSpoofer64.exe"),
    ],
    "BeichenDream/GodPotato":  [
        ("https://github.com/BeichenDream/GodPotato/releases/download/V1.20/GodPotato-NET2.exe",  "GodPotato-NET2.exe"),
        ("https://github.com/BeichenDream/GodPotato/releases/download/V1.20/GodPotato-NET35.exe", "GodPotato-NET35.exe"),
        ("https://github.com/BeichenDream/GodPotato/releases/download/V1.20/GodPotato-NET4.exe",  "GodPotato-NET4.exe"),
    ],
    "ohpe/juicy-potato":      [
        ("https://github.com/ohpe/juicy-potato/releases/download/v0.1/JuicyPotato.exe", "JuicyPotato.exe"),
    ],
    "antonioCoco/RoguePotato":[
        ("https://github.com/antonioCoco/RoguePotato/releases/download/1.0/RoguePotato.zip", "RoguePotato.zip"),
    ],
    "pwntester/ysoserial.net": [
        ("https://github.com/pwntester/ysoserial.net/releases/download/v1.36/ysoserial-1dba9c4416ba6e79b6b262b758fa75e2ee9008e9.zip", "ysoserial.net.zip"),
    ],
    "frohoff/ysoserial":      [
        ("https://github.com/frohoff/ysoserial/releases/download/v0.0.6/ysoserial-all.jar", "ysoserial-all.jar"),
    ],
    "dnspy/dnspy":            [
        ("https://github.com/dnSpy/dnSpy/releases/download/v6.1.8/dnSpy-net-win64.zip", "dnSpy-net-win64.zip"),
    ],
    "qtc-de/remote-method-guesser": [
        ("https://github.com/qtc-de/remote-method-guesser/releases/download/v5.1.0/rmg-5.1.0-jar-with-dependencies.jar", "rmg-5.1.0.jar"),
    ],
    "AlessandroZ/LaZagne": [
        ("https://github.com/AlessandroZ/LaZagne/releases/download/v2.4.7/LaZagne.exe", "LaZagne.exe"),
    ],
    "peass-ng/PEASS-ng": [
        ("https://github.com/peass-ng/PEASS-ng/releases/download/20260422-9567fd62/linpeas.sh",       "linpeas.sh"),
        ("https://github.com/peass-ng/PEASS-ng/releases/download/20260422-9567fd62/linpeas_linux_amd64", "linpeas_linux_amd64"),
        ("https://github.com/peass-ng/PEASS-ng/releases/download/20260422-9567fd62/winPEASany.exe",   "winPEASany.exe"),
        ("https://github.com/peass-ng/PEASS-ng/releases/download/20260422-9567fd62/winPEASx64.exe",   "winPEASx64.exe"),
        ("https://github.com/peass-ng/PEASS-ng/releases/download/20260422-9567fd62/winPEASx86.exe",   "winPEASx86.exe"),
        ("https://github.com/peass-ng/PEASS-ng/releases/download/20260422-9567fd62/winPEAS.bat",      "winPEAS.bat"),
    ],
    "itm4n/PrivescCheck": [
        ("https://github.com/itm4n/PrivescCheck/releases/download/2026.04.16-1/PrivescCheck.ps1", "PrivescCheck.ps1"),
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 120,
         env: dict | None = None) -> tuple[int, str, str]:
    try:
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True,
                           timeout=timeout, env=run_env)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def _git_fetch(src_dir: Path) -> tuple[int, str, str]:
    return _run(["git", "fetch", "--quiet"], cwd=src_dir)


def _git_log_ahead(src_dir: Path) -> str:
    _, out, _ = _run(["git", "log", "HEAD..origin/HEAD", "--oneline", "--no-decorate"], cwd=src_dir)
    return out


def _git_pull(src_dir: Path) -> tuple[int, str, str]:
    return _run(["git", "pull", "--ff-only", "--stat"], cwd=src_dir, timeout=300)


def _git_current_commit(src_dir: Path) -> str:
    _, out, _ = _run(["git", "rev-parse", "--short", "HEAD"], cwd=src_dir)
    return out or "unknown"


def _git_changed_files(src_dir: Path, before: str, after: str) -> list[str]:
    _, out, _ = _run(["git", "diff", "--name-only", before, after], cwd=src_dir)
    return [l for l in out.splitlines() if l]


def _git_clone(repo_slug: str, dest: Path) -> tuple[int, str, str]:
    url = f"https://github.com/{repo_slug}.git"
    return _run(["git", "clone", "--depth=1", url, str(dest)], cwd=TOOLS_DIR, timeout=300)


def _sync_binaries_dir() -> tuple[int, list[str]]:
    """
    Sync p3ta-tricks/binaries/ from tools/*/releases/ and SharpCollection.
    Only compiled binaries are included (no source zips unless it's the only artifact).
    Returns (total_files, log_lines).
    """
    BINARIES_DIR.mkdir(exist_ok=True)
    SC = TOOLS_DIR / "SharpCollection" / "NetFramework_4.7_Any"
    SC_TOOLS = [
        "ADCSPwn", "Certify", "ForgeCert", "Inveigh", "PassTheCert", "Rubeus",
        "SafetyKatz", "Seatbelt", "SharpDPAPI", "SharpMove", "SharpSCCM", "SharpUp",
        "SharpView", "Snaffler", "StandIn", "SweetPotato", "Watson", "Whisker",
    ]
    log = []
    total = 0

    # 1. Sync tools/*/releases/ → binaries/<tool>/
    for tool_dir in sorted(TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir() or tool_dir.name == "SharpCollection":
            continue
        rel = tool_dir / "releases"
        if not rel.exists():
            continue
        files = [f for f in rel.iterdir() if f.is_file()]
        if not files:
            continue
        dest_dir = BINARIES_DIR / tool_dir.name
        dest_dir.mkdir(exist_ok=True)
        for f in files:
            dest = dest_dir / f.name
            try:
                shutil.copy2(f, dest)
                total += 1
            except Exception as e:
                log.append(f"⚠ {tool_dir.name}/{f.name}: {e}")
        log.append(f"✓ {tool_dir.name}: {len(files)} file(s)")

    # 2. Sync SharpCollection → binaries/SharpCollection/
    if SC.exists():
        sc_dest = BINARIES_DIR / "SharpCollection"
        sc_dest.mkdir(exist_ok=True)
        sc_count = 0
        for name in SC_TOOLS:
            for cand in [name, name.replace("-",""), name.replace("_","")]:
                src = SC / f"{cand}.exe"
                if src.exists():
                    dest = sc_dest / f"{name}.exe"
                    shutil.copy2(src, dest)
                    sc_count += 1
                    total += 1
                    break
        log.append(f"✓ SharpCollection: {sc_count} binaries")

    return total, log


def _detect_build_type(tool_path: Path) -> str:
    """
    Detect how to build a tool from source.

    Returns one of:
      'go'         — go.mod present, build with `go build`
      'dotnet'     — .csproj targeting net5+ or net6+/net7+/net8+, use `dotnet build`
      'mono'       — .sln + .NET Framework target (v4.x/v3.x/v2.x), use `msbuild`
      'mingw'      — Makefile.mingw present, cross-compile with x86_64-w64-mingw32
      'python'     — requirements.txt / setup.py / pyproject.toml (install, not compile)
      'powershell' — only .ps1 files (no compilation needed)
      'none'       — unknown or not compilable (data repo, docs only, etc.)
    """
    if (tool_path / "go.mod").exists():
        return "go"

    # Check .csproj for framework version
    csproj_files = list(tool_path.rglob("*.csproj"))
    if csproj_files:
        for cs in csproj_files:
            try:
                content = cs.read_text(errors="ignore")
            except Exception:
                continue
            # net5, net6, net7, net8, net9
            if re.search(r"<TargetFramework>net[5-9]\b", content):
                return "dotnet"
            # net6.0, net8.0-windows, etc.
            if re.search(r"<TargetFramework>net\d+\.\d+", content):
                return "dotnet"
        # Has .csproj but targets .NET Framework → Mono
        if list(tool_path.rglob("*.sln")):
            return "mono"

    if (tool_path / "Makefile.mingw").exists():
        return "mingw"

    if any((tool_path / f).exists() for f in ("requirements.txt", "setup.py", "pyproject.toml")):
        return "python"

    if list(tool_path.glob("*.ps1")) or list(tool_path.rglob("**/*.ps1")):
        # Only treat as powershell if no other build system
        if not list(tool_path.rglob("*.sln")):
            return "powershell"

    return "none"


def _compile_tool(tool_path: Path, build_type: str) -> tuple[int, str, str]:
    """
    Compile/build a tool. On success, output lands in tool_path/releases/.
    Returns (returncode, stdout, stderr).
    """
    releases_dir = tool_path / "releases"
    releases_dir.mkdir(exist_ok=True)
    tool_name = tool_path.name

    if build_type == "go":
        # Find main package location
        main_dirs = set()
        for mf in tool_path.rglob("main.go"):
            main_dirs.add(str(mf.parent.relative_to(tool_path)))
        if not main_dirs:
            return 1, "", "No main.go found"
        out_bin = releases_dir / tool_name
        # Build the first main package found
        pkg_dir = tool_path / sorted(main_dirs)[0]
        env = {"GOOS": "linux", "GOARCH": "amd64"}
        rc, out, err = _run(
            ["go", "build", "-o", str(out_bin), "."],
            cwd=pkg_dir, timeout=600, env=env,
        )
        if rc == 0 and out_bin.exists():
            out_bin.chmod(0o755)
        return rc, out, err

    if build_type == "dotnet":
        sln = list(tool_path.rglob("*.sln"))
        target = str(sln[0]) if sln else "."
        rc, out, err = _run(
            ["dotnet", "build", target, "-c", "Release",
             "--output", str(releases_dir), "--nologo", "-v", "q"],
            cwd=tool_path, timeout=600,
        )
        return rc, out, err

    if build_type == "mono":
        # Find all .csproj files — prefer ones targeting net4x
        csproj_files = list(tool_path.rglob("*.csproj"))
        if not csproj_files:
            return 1, "", "No .csproj file found"

        # Nuget restore: download nuget.exe if not present, run restore on each csproj
        nuget = tool_path / "nuget.exe"
        if not nuget.exists():
            rc_dl, _, err_dl = _run(
                ["curl", "-L", "--silent", "--fail", "-o", str(nuget),
                 "https://dist.nuget.org/win-x86-commandline/latest/nuget.exe"],
                timeout=60,
            )
            if rc_dl != 0:
                return 1, "", f"Failed to download nuget.exe: {err_dl}"

        for cs in csproj_files:
            _run(
                ["mono", str(nuget), "restore", str(cs), "-PackagesDirectory",
                 str(tool_path / "packages")],
                cwd=tool_path, timeout=300,
            )
            # Also install packages referenced by HintPaths but missing version
            pkg_cfg = cs.parent / "packages.config"
            if pkg_cfg.exists():
                _run(
                    ["mono", str(nuget), "restore", str(pkg_cfg),
                     "-PackagesDirectory", str(tool_path / "packages")],
                    cwd=tool_path, timeout=300,
                )

        # Build each csproj
        built_any = False
        all_errors = []
        for cs in csproj_files:
            rc, out, err = _run(
                ["msbuild", str(cs),
                 "/p:Configuration=Release",
                 "/p:Platform=Any CPU",
                 "/v:q", "/nologo"],
                cwd=tool_path, timeout=600,
            )
            if rc == 0:
                built_any = True
            else:
                all_errors.append(err[-300:])

        if built_any:
            for exe in tool_path.rglob("bin/Release/**/*.exe"):
                shutil.copy2(exe, releases_dir / exe.name)
            for dll in tool_path.rglob("bin/Release/**/*.dll"):
                dest = releases_dir / dll.name
                if not dest.exists():
                    shutil.copy2(dll, dest)
            # Clean up nuget.exe
            if nuget.exists():
                nuget.unlink()
            return 0, f"Built {len(list(releases_dir.iterdir()))} file(s)", ""
        return 1, "", "\n".join(all_errors)

    if build_type == "mingw":
        # nanodump-style: Makefile.mingw uses x86_64-w64-mingw32-cc
        rc, out, err = _run(
            ["make", "-f", "Makefile.mingw"],
            cwd=tool_path, timeout=600,
        )
        if rc == 0:
            # Copy any generated files in dist/ or current dir to releases/
            for f in list((tool_path / "dist").glob("*") if (tool_path / "dist").exists() else []):
                if f.is_file():
                    shutil.copy2(f, releases_dir / f.name)
        return rc, out, err

    if build_type == "python":
        req = tool_path / "requirements.txt"
        if req.exists():
            rc, out, err = _run(
                [sys.executable, "-m", "pip", "install", "-r", str(req),
                 "--break-system-packages"],
                cwd=tool_path, timeout=300,
            )
            if rc != 0:
                rc, out, err = _run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req)],
                    cwd=tool_path, timeout=300,
                )
            return rc, out or "pip install complete", err
        setup = tool_path / "setup.py"
        if setup.exists():
            return _run(
                [sys.executable, "-m", "pip", "install", "-e", ".",
                 "--break-system-packages"],
                cwd=tool_path, timeout=300,
            )
        return 0, "No requirements.txt or setup.py — nothing to install", ""

    return 1, "", f"Unsupported build type: {build_type}"


def _download_release_asset(url: str, dest: Path) -> tuple[bool, str]:
    """Download a single release asset. Returns (success, message)."""
    rc, _, err = _run(
        ["curl", "-L", "--silent", "--fail", "-o", str(dest), url],
        timeout=300,
    )
    if rc != 0:
        return False, f"curl failed: {err[:80]}"
    # Extract archives transparently
    if dest.name.endswith(".gz") and not dest.name.endswith(".tar.gz"):
        import gzip
        out_path = dest.with_suffix("")
        with gzip.open(dest, "rb") as fi, open(out_path, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        out_path.chmod(0o755)
        dest.unlink()
    return True, "ok"


def _unique_dirs(registry: dict) -> set[str]:
    return set(registry.values())


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

app = Server("p3ta-tricks-maintenance")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ── Wiki source tools ──────────────────────────────────────────────
        Tool(
            name="list_sources",
            description="List all registered wiki sources with their type, directory, and label.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="source_status",
            description="Show current commit and git status for all wiki sources.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="check_updates",
            description=(
                "Check all p3ta-tricks git sources for upstream changes without pulling. "
                "Returns which sources have new commits and what changed."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="pull_updates",
            description=(
                "Pull latest changes from upstream for one or all git sources, then rebuild the index. "
                "Pass source_ids to update specific sources, or omit to update all."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "e.g. ['hacktricks', 'gtfobins']. Omit for all.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="rebuild_index",
            description="Rebuild the p3ta-tricks search index (scripts/build.py). Run after any content changes.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="restart_server",
            description=(
                "Restart a p3ta-tricks Flask server. "
                "mode='online' → port 5000 (no WATT, live GitHub links). "
                "mode='watt'   → port 5001 (WATT_MODE=1, local tools, offline)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["online", "watt"],
                        "description": "'online' (port 5000) or 'watt' (port 5001, offline).",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="update_all",
            description=(
                "Full maintenance run for ONLINE mode: "
                "pull all wiki sources → rebuild index → restart online server (port 5000). "
                "Does NOT touch watt tools or compile anything."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # ── WATT tool management ───────────────────────────────────────────
        Tool(
            name="watt_tool_status",
            description=(
                "Show which watt tools are cloned, their commits, build type, "
                "and whether compiled/release binaries exist."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="install_missing_tools",
            description=(
                "Clone any registered watt tools that are not yet downloaded. "
                "Pass tool_names to install specific ones, or omit to clone all missing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Local dir names, e.g. ['Rubeus', 'Certipy']. Omit for all missing.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="check_tool_updates",
            description="Check all cloned watt tools for upstream changes without pulling.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="update_watt_tools",
            description=(
                "Git pull all already-cloned watt tools. "
                "Pass tool_names to update specific tools, or omit to update all."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Local dir names to update. Omit for all.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="compile_tool",
            description=(
                "Compile/build a single tool from source and place output in tools/<name>/releases/. "
                "Auto-detects: Go (go build), dotnet (net5+), mono/msbuild (.NET Framework), "
                "mingw (Makefile.mingw cross-compile for BOF/C tools like nanodump), "
                "python (pip install -r requirements.txt). "
                "PetitPotam and RottenPotatoNG use MSVC-only C++ and cannot be compiled on Linux."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Local dir name of the tool, e.g. 'GoldenGMSA', 'nanodump'.",
                    },
                    "build_type": {
                        "type": "string",
                        "enum": ["auto", "go", "dotnet", "mono", "mingw", "python"],
                        "description": "Force a build method. Default 'auto' detects from source.",
                    },
                },
                "required": ["tool_name"],
            },
        ),
        Tool(
            name="compile_all_tools",
            description=(
                "Attempt to compile all cloned tools that have compilable source. "
                "Skips: tools with existing releases/, tools that are python/ps1-only, "
                "tools already covered by SharpCollection, MSVC-only C++ tools. "
                "Reports what succeeded, what failed, and why."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "If true, recompile even if releases/ already has files.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="sync_releases",
            description=(
                "Re-download all pre-built release binaries from GitHub for tools in RELEASE_REGISTRY. "
                "Use this to refresh binaries after update_watt_tools, or to restore deleted files. "
                "Pass tool_names to sync specific tools only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Local dir names to re-download releases for. Omit for all.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="watt_diff",
            description=(
                "Show the differences between ONLINE mode and WATT mode: "
                "which sources/features exist in each, what is available offline vs online-only, "
                "tool binary coverage, and what would break offline."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="update_watt",
            description=(
                "Full offline mode maintenance run: "
                "pull all tools → re-download release binaries → compile compilable tools "
                "→ sync binaries/ directory → restart offline server (port 5001). "
                "This is the 'update offline mode' command."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="sync_binaries",
            description=(
                "Sync the p3ta-tricks/binaries/ directory from tools/*/releases/ and SharpCollection. "
                "Run this after compile_tool, sync_releases, or update_watt_tools to make new binaries "
                "available on the /binaries/ page in both online and offline modes. "
                "This is the only tool that writes to binaries/ — everything else writes to tools/*/releases/ first."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    # ─────────────────────────────────────────────────────────────────────────
    # Wiki source tools
    # ─────────────────────────────────────────────────────────────────────────

    if name == "list_sources":
        lines = ["## p3ta-tricks Sources\n"]
        for sid, cfg in SOURCE_REGISTRY.items():
            d = SOURCES / cfg["dir"]
            exists = "✓" if d.exists() else "✗ missing"
            git_tag = "git" if cfg["git"] else "plain"
            lines.append(f"- **{sid}** ({git_tag}) — {cfg['label']} — `sources/{cfg['dir']}` {exists}")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "source_status":
        lines = [f"## Source Status — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        for sid, cfg in SOURCE_REGISTRY.items():
            d = SOURCES / cfg["dir"]
            if not d.exists():
                lines.append(f"- **{sid}**: directory missing")
                continue
            if not cfg["git"]:
                lines.append(f"- **{sid}** (plain): no git tracking")
                continue
            commit = _git_current_commit(d)
            _, status_out, _ = _run(["git", "status", "--short"], cwd=d)
            local_changes = len(status_out.splitlines()) if status_out else 0
            lines.append(f"- **{sid}**: `{commit}` | {local_changes} local changes")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "check_updates":
        lines = [f"## Checking upstream — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        has_updates = []
        for sid, cfg in SOURCE_REGISTRY.items():
            d = SOURCES / cfg["dir"]
            if not cfg["git"] or not d.exists():
                continue
            rc, _, err = _git_fetch(d)
            if rc != 0:
                lines.append(f"- **{sid}**: fetch failed — {err}")
                continue
            ahead = _git_log_ahead(d)
            if ahead:
                count = len(ahead.splitlines())
                has_updates.append(sid)
                lines.append(f"- **{sid}**: {count} new commit{'s' if count > 1 else ''}")
                for l in ahead.splitlines()[:5]:
                    lines.append(f"  - {l}")
                if count > 5:
                    lines.append(f"  - … and {count - 5} more")
            else:
                lines.append(f"- **{sid}**: up to date")
        if has_updates:
            lines.append(f"\n**{len(has_updates)} source(s) have updates:** {', '.join(has_updates)}")
            lines.append("\nRun `pull_updates` or `update_all` to apply.")
        else:
            lines.append("\nAll sources are up to date.")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "pull_updates":
        requested = arguments.get("source_ids") or []
        targets = {sid: cfg for sid, cfg in SOURCE_REGISTRY.items()
                   if cfg["git"] and (not requested or sid in requested)}
        lines = [f"## Pulling updates — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        changed_any = False
        for sid, cfg in targets.items():
            d = SOURCES / cfg["dir"]
            if not d.exists():
                lines.append(f"- **{sid}**: directory missing, skipping")
                continue
            before = _git_current_commit(d)
            _git_fetch(d)
            rc, out, err = _git_pull(d)
            after = _git_current_commit(d)
            if rc != 0:
                lines.append(f"- **{sid}**: pull failed — {err}")
            elif before == after:
                lines.append(f"- **{sid}**: already up to date (`{before}`)")
            else:
                changed = _git_changed_files(d, before, after)
                changed_any = True
                lines.append(f"- **{sid}**: `{before}` → `{after}` | {len(changed)} files changed")
                for f in changed[:8]:
                    lines.append(f"  - {f}")
                if len(changed) > 8:
                    lines.append(f"  - … and {len(changed) - 8} more")
        if changed_any:
            lines.append("\n---\nRebuilding search index…")
            rc, out, err = _run([sys.executable, str(BUILD_SCRIPT)], timeout=300)
            lines.append("Index rebuilt." if rc == 0 else f"Index build failed:\n```\n{err}\n```")
        else:
            lines.append("\nNo changes — index rebuild skipped.")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "rebuild_index":
        lines = [f"## Rebuilding index — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        rc, out, err = _run([sys.executable, str(BUILD_SCRIPT)], timeout=300)
        if rc == 0:
            counts = [l for l in out.splitlines() if "INFO" in l and l.strip().split()[-1].isdigit()]
            lines.append("Index rebuilt successfully.\n")
            for c in counts:
                lines.append(f"  {c.split('INFO:')[-1].strip()}")
        else:
            lines.append(f"Build failed:\n```\n{err}\n```")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "restart_server":
        mode = arguments.get("mode", "online")
        port = 5001 if mode == "watt" else 5000
        _run(["bash", "-c", f"kill $(lsof -ti:{port}) 2>/dev/null; true"])
        await asyncio.sleep(1)
        if mode == "watt":
            subprocess.Popen(
                ["bash", str(WATT_ROOT / "start.sh")],
                stdout=open("/tmp/p3ta-watt.log", "w"),
                stderr=subprocess.STDOUT,
                cwd=str(WATT_ROOT),
            )
        else:
            subprocess.Popen(
                [sys.executable, str(ROOT / "app.py")],
                stdout=open("/tmp/p3ta-flask.log", "w"),
                stderr=subprocess.STDOUT,
                cwd=ROOT,
            )
        await asyncio.sleep(2)
        log = "/tmp/p3ta-watt.log" if mode == "watt" else "/tmp/p3ta-flask.log"
        rc, out, _ = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://127.0.0.1:{port}/"])
        status = "✓ server responding" if out == "200" else f"⚠ HTTP {out}"
        diff_note = (
            "\n\n**ONLINE vs WATT differences:**\n"
            "- ONLINE (5000): GitHub links live, no /tools/ routes, internet required\n"
            "- WATT (5001):   GitHub links → local tool dirs, /tools/ routes active, fully offline"
        ) if mode == "online" else ""
        return [TextContent(type="text", text=f"Server ({mode}, port {port}) restarted. {status}\nLog: {log}{diff_note}")]

    if name == "update_all":
        lines = [f"# p3ta-tricks Online Update — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        changed_sources = []
        lines.append("## Step 1: Pulling wiki sources\n")
        for sid, cfg in SOURCE_REGISTRY.items():
            if not cfg["git"]:
                continue
            d = SOURCES / cfg["dir"]
            if not d.exists():
                lines.append(f"- **{sid}**: missing")
                continue
            before = _git_current_commit(d)
            _git_fetch(d)
            rc, out, err = _git_pull(d)
            after = _git_current_commit(d)
            if rc != 0:
                lines.append(f"- **{sid}**: ⚠ {err[:80]}")
            elif before == after:
                lines.append(f"- **{sid}**: up to date")
            else:
                changed = _git_changed_files(d, before, after)
                changed_sources.append((sid, len(changed)))
                lines.append(f"- **{sid}**: ✓ {len(changed)} file(s) (`{before[:7]}` → `{after[:7]}`)")
                for f in changed[:5]:
                    lines.append(f"  - {f}")
                if len(changed) > 5:
                    lines.append(f"  - … +{len(changed) - 5} more")

        lines.append("\n## Step 2: Rebuilding index\n")
        rc, out, err = _run([sys.executable, str(BUILD_SCRIPT)], timeout=300)
        lines.append("Index rebuilt." if rc == 0 else f"⚠ Build failed:\n```\n{err[:500]}\n```")

        lines.append("\n## Step 3: Restarting online server (port 5000)\n")
        _run(["bash", "-c", "kill $(lsof -ti:5000) 2>/dev/null; true"])
        await asyncio.sleep(1)
        subprocess.Popen(
            [sys.executable, str(ROOT / "app.py")],
            stdout=open("/tmp/p3ta-flask.log", "w"),
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )
        await asyncio.sleep(2)
        rc2, code, _ = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:5000/"])
        lines.append("✓ Server up." if code == "200" else f"⚠ HTTP {code}")

        lines.append("\n## Summary\n")
        if changed_sources:
            lines.append(f"Updated: " + ", ".join(f"{s} ({n} files)" for s, n in changed_sources))
        else:
            lines.append("All wiki sources were already up to date.")
        lines.append("\nNote: To update WATT offline tools, run `update_watt` instead.")
        return [TextContent(type="text", text="\n".join(lines))]

    # ─────────────────────────────────────────────────────────────────────────
    # WATT tool management
    # ─────────────────────────────────────────────────────────────────────────

    if name == "watt_tool_status":
        SC = TOOLS_DIR / "SharpCollection" / "NetFramework_4.7_Any"
        lines = [f"## WATT Tool Status — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        lines.append(f"Tools dir: `{TOOLS_DIR}`\n")
        seen = set()
        cloned, missing_list = [], []
        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen:
                continue
            seen.add(dir_name)
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists():
                missing_list.append(f"- ✗ **{dir_name}**")
                continue
            commit = _git_current_commit(tool_path) if (tool_path / ".git").exists() else "no-git"
            build_type = _detect_build_type(tool_path)
            # Binary coverage
            has_releases = (tool_path / "releases").exists() and any((tool_path / "releases").iterdir())
            # Check SharpCollection
            in_sc = any(
                (SC / f"{c}.exe").exists()
                for c in [dir_name, dir_name.replace("-",""), dir_name.replace("_","")]
            ) if SC.exists() else False
            if has_releases:
                bin_status = "✓ releases/"
            elif in_sc:
                bin_status = "✓ SharpCollection"
            elif build_type in ("python", "powershell"):
                bin_status = f"— {build_type}"
            elif build_type != "none":
                bin_status = f"⚠ compilable ({build_type}), no binary"
            else:
                bin_status = "— no binary"
            cloned.append(f"- ✓ **{dir_name}** `{commit}` | {bin_status} | build:{build_type}")
        lines.append(f"### Cloned ({len(cloned)})\n")
        lines.extend(cloned)
        lines.append(f"\n### Missing ({len(missing_list)})\n")
        lines.extend(missing_list)
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "install_missing_tools":
        requested = set(arguments.get("tool_names") or [])
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        lines = [f"## Installing missing watt tools — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        seen, installed, failed, skipped = set(), [], [], []
        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen:
                continue
            seen.add(dir_name)
            if requested and dir_name not in requested:
                continue
            tool_path = TOOLS_DIR / dir_name
            if tool_path.exists():
                skipped.append(dir_name)
                continue
            lines.append(f"- Cloning **{dir_name}** from github.com/{slug}…")
            rc, _, err = _git_clone(slug, tool_path)
            if rc == 0:
                commit = _git_current_commit(tool_path)
                installed.append(dir_name)
                lines[-1] += f" ✓ ({commit})"
            else:
                failed.append(dir_name)
                lines[-1] += f" ✗ {err[:80]}"
        lines.append(f"\nInstalled: {len(installed)} | Failed: {len(failed)} | Already present: {len(skipped)}")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "check_tool_updates":
        lines = [f"## Checking watt tools for updates — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        has_updates = []
        seen = set()
        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen:
                continue
            seen.add(dir_name)
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists() or not (tool_path / ".git").exists():
                continue
            rc, _, err = _git_fetch(tool_path)
            if rc != 0:
                lines.append(f"- **{dir_name}**: fetch failed — {err[:60]}")
                continue
            ahead = _git_log_ahead(tool_path)
            if ahead:
                count = len(ahead.splitlines())
                has_updates.append(dir_name)
                lines.append(f"- **{dir_name}**: {count} new commit{'s' if count > 1 else ''}")
            else:
                lines.append(f"- **{dir_name}**: up to date")
        if has_updates:
            lines.append(f"\n**{len(has_updates)} tool(s) have updates:** {', '.join(has_updates)}")
        else:
            lines.append("\nAll cloned tools are up to date.")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "update_watt_tools":
        requested = set(arguments.get("tool_names") or [])
        lines = [f"## Updating watt tools — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        seen = set()
        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen:
                continue
            seen.add(dir_name)
            if requested and dir_name not in requested:
                continue
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists():
                lines.append(f"- **{dir_name}**: not cloned (use install_missing_tools)")
                continue
            if not (tool_path / ".git").exists():
                lines.append(f"- **{dir_name}**: no .git, skipping")
                continue
            before = _git_current_commit(tool_path)
            _git_fetch(tool_path)
            rc, _, err = _git_pull(tool_path)
            after = _git_current_commit(tool_path)
            if rc != 0:
                lines.append(f"- **{dir_name}**: ⚠ {err[:80]}")
            elif before == after:
                lines.append(f"- **{dir_name}**: up to date")
            else:
                lines.append(f"- **{dir_name}**: ✓ `{before[:7]}` → `{after[:7]}`")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "compile_tool":
        tool_name = arguments.get("tool_name", "").strip()
        forced_type = arguments.get("build_type", "auto")
        if not tool_name:
            return [TextContent(type="text", text="Error: tool_name required")]
        tool_path = TOOLS_DIR / tool_name
        if not tool_path.exists():
            return [TextContent(type="text", text=f"Tool not found: {tool_path}")]

        build_type = forced_type if forced_type != "auto" else _detect_build_type(tool_path)
        if build_type == "none":
            return [TextContent(type="text", text=f"**{tool_name}**: no compilable source detected (data/docs repo, or MSVC-only C++)")]
        if build_type == "powershell":
            return [TextContent(type="text", text=f"**{tool_name}**: PowerShell — no compilation needed, use scripts directly")]

        lines = [f"## Compiling {tool_name} ({build_type}) — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        rc, out, err = _compile_tool(tool_path, build_type)
        releases = list((tool_path / "releases").iterdir()) if (tool_path / "releases").exists() else []
        if rc == 0:
            lines.append(f"✓ Build succeeded.")
            if releases:
                lines.append(f"\nOutput in releases/:")
                for f in releases:
                    sz = f.stat().st_size
                    sz_str = f"{sz/1048576:.1f}MB" if sz > 1048576 else f"{sz/1024:.0f}KB"
                    lines.append(f"  - {f.name} ({sz_str})")
        else:
            lines.append(f"✗ Build failed (rc={rc})")
            if err:
                lines.append(f"\nStderr:\n```\n{err[-2000:]}\n```")
            if out:
                lines.append(f"\nStdout:\n```\n{out[-1000:]}\n```")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "compile_all_tools":
        force = arguments.get("force", False)
        SC = TOOLS_DIR / "SharpCollection" / "NetFramework_4.7_Any"
        lines = [f"## Compiling all compilable tools — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

        # Tools that are MSVC-only C++ — cannot be compiled on Linux
        msvc_only = {"PetitPotam", "RottenPotatoNG"}
        # Tools covered by SharpCollection — don't re-compile from source
        sc_covered = set()
        if SC.exists():
            for p in SC.glob("*.exe"):
                sc_covered.add(p.stem)

        seen = set()
        results = {"success": [], "failed": [], "skipped": []}

        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen:
                continue
            seen.add(dir_name)
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists():
                continue
            if dir_name in msvc_only:
                results["skipped"].append(f"- **{dir_name}**: MSVC-only C++ (PetitPotam/RottenPotatoNG use COM RPC, no MinGW support)")
                continue
            # Skip if in SharpCollection
            if any(dir_name.replace("-","") == s or dir_name == s for s in sc_covered):
                results["skipped"].append(f"- **{dir_name}**: covered by SharpCollection")
                continue
            releases_dir = tool_path / "releases"
            if not force and releases_dir.exists() and any(releases_dir.iterdir()):
                results["skipped"].append(f"- **{dir_name}**: releases/ already has files (use force=true to recompile)")
                continue

            build_type = _detect_build_type(tool_path)
            if build_type in ("none", "powershell"):
                continue
            if build_type == "python":
                results["skipped"].append(f"- **{dir_name}**: python — use install_deps.sh for pip install")
                continue

            lines.append(f"- Compiling **{dir_name}** ({build_type})…")
            rc, out, err = _compile_tool(tool_path, build_type)
            if rc == 0:
                out_files = list(releases_dir.iterdir()) if releases_dir.exists() else []
                results["success"].append(dir_name)
                lines[-1] += f" ✓ ({len(out_files)} file(s))"
            else:
                results["failed"].append(dir_name)
                lines[-1] += f" ✗"
                lines.append(f"  ```\n  {err[-300:]}\n  ```")

        lines.append(f"\n## Result\n")
        lines.append(f"✓ Compiled: {len(results['success'])}: {', '.join(results['success']) or 'none'}")
        lines.append(f"✗ Failed:   {len(results['failed'])}: {', '.join(results['failed']) or 'none'}")
        lines.append(f"— Skipped:  {len(results['skipped'])}")
        for s in results["skipped"]:
            lines.append(f"  {s}")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "sync_releases":
        requested = set(arguments.get("tool_names") or [])
        # Build slug→dir lookup
        slug_to_dir = {slug: dir_name for slug, dir_name in TOOL_REGISTRY.items()}
        lines = [f"## Syncing release binaries — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

        for slug, assets in RELEASE_REGISTRY.items():
            dir_name = slug_to_dir.get(slug, slug.split("/")[-1])
            if requested and dir_name not in requested:
                continue
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists():
                lines.append(f"- **{dir_name}**: not cloned, skipping")
                continue
            releases_dir = tool_path / "releases"
            releases_dir.mkdir(exist_ok=True)
            lines.append(f"- **{dir_name}**:")
            for url, filename in assets:
                dest = releases_dir / filename
                ok, msg = _download_release_asset(url, dest)
                sz = f" ({dest.stat().st_size / 1048576:.1f}MB)" if ok and dest.exists() else ""
                lines.append(f"  {'✓' if ok else '✗'} {filename}{sz}" + (f" — {msg}" if not ok else ""))

        return [TextContent(type="text", text="\n".join(lines))]

    if name == "watt_diff":
        SC = TOOLS_DIR / "SharpCollection" / "NetFramework_4.7_Any"
        lines = ["# ONLINE vs WATT Mode Differences\n"]

        lines.append("## Mode Overview\n")
        lines.append("| Feature | ONLINE (port 5000) | WATT (port 5001) |")
        lines.append("|---------|-------------------|-----------------|")
        lines.append("| Wiki pages | ✓ | ✓ same content |")
        lines.append("| Search index | ✓ | ✓ same index |")
        lines.append("| GitHub tool links | → github.com (live) | → /tools/ (local) |")
        lines.append("| /tools/ routes | ✗ | ✓ directory browser |")
        lines.append("| Pre-built binary downloads | ✗ | ✓ |")
        lines.append("| Internet required | Yes | No |")
        lines.append("| External doc links | Work | Broken (blog/MS docs) |")

        lines.append("\n## Wiki Sources (both modes)\n")
        for sid, cfg in SOURCE_REGISTRY.items():
            d = SOURCES / cfg["dir"]
            exists = "✓" if d.exists() else "✗ missing"
            lines.append(f"- {sid}: {exists}")

        lines.append("\n## Tool Binary Coverage (WATT only)\n")
        lines.append("### With pre-built release binaries in releases/")
        seen = set()
        with_releases, with_sc, compile_needed, script_only = [], [], [], []
        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen:
                continue
            seen.add(dir_name)
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists():
                continue
            bt = _detect_build_type(tool_path)
            has_rel = (tool_path / "releases").exists() and any((tool_path / "releases").iterdir())
            in_sc = SC.exists() and any(
                (SC / f"{c}.exe").exists()
                for c in [dir_name, dir_name.replace("-",""), dir_name.replace("_","")]
            )
            if has_rel:
                rel_files = list((tool_path / "releases").iterdir())
                with_releases.append(f"  - **{dir_name}**: {', '.join(f.name for f in rel_files[:3])}")
            elif in_sc:
                with_sc.append(f"  - **{dir_name}** (SharpCollection pre-built)")
            elif bt in ("go", "dotnet", "mono", "mingw"):
                compile_needed.append(f"  - **{dir_name}** (build: {bt}) — run compile_tool")
            elif bt in ("python", "powershell", "none"):
                script_only.append(f"  - **{dir_name}** ({bt})")

        lines.extend(with_releases)
        lines.append("\n### Via SharpCollection (GhostPack pre-compiled)")
        lines.extend(with_sc)
        lines.append("\n### Compilable from source (no binary yet)")
        lines.extend(compile_needed)
        lines.append("\n### Script-only (Python/PS1 — no binary needed)")
        lines.extend(script_only)

        lines.append("\n## External Links Broken Offline\n")
        lines.append("These reference sites cannot be mirrored and will 404 offline:")
        lines.append("- portswigger.net (~296 links) — PortSwigger Web Security Academy")
        lines.append("- learn.microsoft.com (~271 links) — Microsoft Docs")
        lines.append("- medium.com (~155 links) — Blog posts")
        lines.append("- youtube.com (~165 links) — Videos")
        lines.append("- posts.specterops.io (~116 links) — SpecterOps blog")
        lines.append("- 0xdf.gitlab.io (~111 links) — HTB writeups")
        lines.append("- nvd.nist.gov (~53 links) — CVE database")
        lines.append("- attack.mitre.org (~35 links) — ATT&CK")
        lines.append("\nAll tool GitHub links are intercepted and redirected to local copies.")

        return [TextContent(type="text", text="\n".join(lines))]

    if name == "update_watt":
        lines = [f"# WATT Full Update — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

        lines.append("## Step 1: Pulling watt tools\n")
        seen, tool_updates = set(), []
        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen:
                continue
            seen.add(dir_name)
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists() or not (tool_path / ".git").exists():
                continue
            before = _git_current_commit(tool_path)
            _git_fetch(tool_path)
            rc, _, err = _git_pull(tool_path)
            after = _git_current_commit(tool_path)
            if rc != 0:
                lines.append(f"- **{dir_name}**: ⚠ {err[:60]}")
            elif before != after:
                tool_updates.append(dir_name)
                lines.append(f"- **{dir_name}**: ✓ `{before[:7]}` → `{after[:7]}`")
        if not tool_updates:
            lines.append("All tools already up to date.")

        lines.append("\n## Step 2: Refreshing release binaries\n")
        slug_to_dir = {slug: dir_name for slug, dir_name in TOOL_REGISTRY.items()}
        for slug, assets in RELEASE_REGISTRY.items():
            dir_name = slug_to_dir.get(slug, slug.split("/")[-1])
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists():
                continue
            releases_dir = tool_path / "releases"
            releases_dir.mkdir(exist_ok=True)
            tool_ok = True
            for url, filename in assets:
                dest = releases_dir / filename
                ok, msg = _download_release_asset(url, dest)
                if not ok:
                    tool_ok = False
                    lines.append(f"- **{dir_name}/{filename}**: ✗ {msg}")
            if tool_ok:
                lines.append(f"- **{dir_name}**: ✓ {len(assets)} asset(s)")

        lines.append("\n## Step 3: Compiling compilable tools\n")
        msvc_only = {"PetitPotam", "RottenPotatoNG"}
        SC = TOOLS_DIR / "SharpCollection" / "NetFramework_4.7_Any"
        sc_covered = {p.stem for p in SC.glob("*.exe")} if SC.exists() else set()
        seen2 = set()
        for slug, dir_name in TOOL_REGISTRY.items():
            if dir_name in seen2:
                continue
            seen2.add(dir_name)
            if dir_name in msvc_only:
                continue
            tool_path = TOOLS_DIR / dir_name
            if not tool_path.exists():
                continue
            releases_dir = tool_path / "releases"
            if releases_dir.exists() and any(releases_dir.iterdir()):
                continue  # already has binaries
            if any(dir_name.replace("-","") == s or dir_name == s for s in sc_covered):
                continue
            bt = _detect_build_type(tool_path)
            if bt in ("none", "python", "powershell"):
                continue
            lines.append(f"- Compiling **{dir_name}** ({bt})…")
            rc, out, err = _compile_tool(tool_path, bt)
            out_files = list(releases_dir.iterdir()) if releases_dir.exists() else []
            if rc == 0:
                lines[-1] += f" ✓ ({len(out_files)} file(s))"
            else:
                lines[-1] += f" ✗"
                lines.append(f"  {err[-200:]}")

        lines.append("\n## Step 4: Syncing binaries/ directory\n")
        total_bins, bin_log = _sync_binaries_dir()
        lines.append(f"Synced {total_bins} binary file(s) to p3ta-tricks/binaries/")

        lines.append("\n## Step 5: Restarting offline server (port 5001)\n")
        _run(["bash", "-c", "kill $(lsof -ti:5001) 2>/dev/null; true"])
        await asyncio.sleep(1)
        subprocess.Popen(
            ["bash", str(WATT_ROOT / "start.sh")],
            stdout=open("/tmp/p3ta-offline.log", "w"),
            stderr=subprocess.STDOUT,
            cwd=str(WATT_ROOT),
        )
        await asyncio.sleep(2)
        rc2, code, _ = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:5001/"])
        lines.append("✓ Offline server up." if code == "200" else f"⚠ HTTP {code}")

        lines.append(f"\n## Summary\n")
        lines.append(f"Tools pulled: {len(tool_updates)}: {', '.join(tool_updates) or 'none updated'}")
        lines.append(f"Release binaries: refreshed from RELEASE_REGISTRY ({len(RELEASE_REGISTRY)} tool sets)")
        lines.append(f"Binaries dir: {total_bins} files synced to /binaries/")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "sync_binaries":
        lines = [f"## Syncing binaries/ — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        total, log = _sync_binaries_dir()
        lines.extend(log)
        lines.append(f"\nTotal: {total} binary file(s) now in p3ta-tricks/binaries/")
        lines.append("Available at /binaries/ on both online and offline servers.")
        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
