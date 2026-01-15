# Available Tools - DFIR Attack & Defend Lab

## Virtualization
- **VirtualBox** - Free, cross-platform hypervisor
- **VMware Workstation/Player** - Commercial/free options
- **Hyper-V** - Windows native hypervisor (Pro/Enterprise)

## Operating Systems
- **Windows Server 2019/2022** - Domain Controller (evaluation)
- **Windows 10/11** - Client workstation (evaluation)
- **Kali Linux** - Attack/penetration testing platform
- **Ubuntu** - General purpose Linux

---

## Defensive / Blue Team Tools

### SIEM & Log Analysis
- **Splunk Enterprise** - Log aggregation and analysis (free tier: 500MB/day)
- **Splunk Universal Forwarder** - Agent for log shipping

### EDR & Endpoint Visibility
- **Velociraptor** - Open source EDR, forensic collection, and hunting
- **Sysmon** - Windows system monitoring (Sysinternals)
- **SwiftOnSecurity Sysmon Config** - Community Sysmon configuration

### Network Detection
- **Wireshark** - Network traffic capture and analysis
- **Zeek (Bro)** - Network security monitoring

### Timeline & Forensic Analysis
- **Timesketch** - Collaborative forensic timeline analysis
- **Plaso/Log2Timeline** - Super timeline generation
- **KAPE** - Kroll Artifact Parser and Extractor

---

## Forensic Workstation VMs (Pre-built)
- **SIFT Workstation** - SANS forensic tools (Linux)
- **Flare VM** - Mandiant malware analysis tools (Windows)
- **REMnux** - Reverse engineering malware (Linux)
- **Kali Linux** - Light forensic tools included

---

## Forensic Analysis Tools

### Image Mounting
- **Arsenal Image Mounter** - Mount disk images (free)
- **FTK Imager** - Disk imaging and mounting (free)

### Forensic Suites
- **Autopsy** - Open source digital forensics platform
- **KAPE** - Artifact collection and processing

### Windows Analysis
- **Eric Zimmerman Tools** - Registry, filesystem, timeline tools
- **RegRipper** - Registry hive parsing
- **Event Log Explorer** - Windows event log analysis
- **Windows Sysinternals** - Autoruns, Process Explorer, etc.

### Memory Analysis
- **Volatility 3** - Memory forensics framework
- **MemProcFS** - Memory process file system

### Browser Forensics
- **Nirsoft Tools** - Browser history, password recovery

### Malware Analysis
- **PEStudio** - PE file static analysis
- **CyberChef** - Data encoding/decoding Swiss army knife
- **scdbg** - Shellcode analysis
- **ExifTool** - Metadata extraction

---

## Offensive / Red Team Tools

### C2 Frameworks
- **Empire** - PowerShell post-exploitation framework
- **Metasploit** - Penetration testing framework
- **Sliver** - Cross-platform C2 framework

### Credential Tools
- **Mimikatz** - Windows credential extraction (via Empire)
- **Impacket** - Python network protocol tools

### Reconnaissance
- **BloodHound** - Active Directory attack path mapping
- **PowerView** - AD enumeration (PowerSploit)

### Lateral Movement
- **PsExec** - Remote command execution
- **WMI/WinRM** - Windows management tools
- **SMB** - File share access

### Ransomware Simulation
- **Ransomware simulators** - Safe encryption simulation tools

---

## Data Sources for Training
- **Splunk BOTS (Boss of the SOC)** - Free Splunk challenge datasets
  - GitHub: https://github.com/splunk/botsv3
- **DFIR Artifact Collections** - Various CTF and challenge data

---

## File Operations
- Read/write within repository
- No destructive deletes without confirmation
- VM snapshots for recovery

## External Access
- **Internet:** Restricted (lab VMs should be isolated)
- **Package managers:** apt, pip, chocolatey (on appropriate systems)

## Usage Rules
- Prefer existing tools over new ones
- Explain why a tool is needed before installing
- Document all tool configurations
- Maintain tool version information for reproducibility
