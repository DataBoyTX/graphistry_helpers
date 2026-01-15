# TODO - DFIR Attack & Defend Lab

## Now (Phase 1: Foundation)
- [ ] Download Windows Server 2022 evaluation ISO (manual: https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2022)
- [ ] Download Windows 10 Enterprise evaluation ISO (manual: https://www.microsoft.com/en-us/evalcenter/evaluate-windows-10-enterprise)

## Next (Phase 1 continued)
- [ ] Create Windows Server VM (4GB RAM, 60GB disk)
- [ ] Install Windows Server and promote to Domain Controller
- [ ] Configure Active Directory Domain Services
- [ ] Create test user accounts (alice, bob, admin)
- [ ] Create Windows Client VM (4GB RAM, 40GB disk)
- [ ] Join Windows Client to domain
- [ ] Configure all VMs on internal network (192.168.56.X)
- [ ] Verify network connectivity between all VMs
- [ ] Take baseline snapshots of all VMs

## Later (Phase 2: Defensive Tooling)
- [ ] Enable PowerShell Module Logging (GPO)
- [ ] Enable PowerShell ScriptBlock Logging (GPO)
- [ ] Enable PowerShell Transcription (GPO)
- [ ] Download Sysmon from Sysinternals
- [ ] Download SwiftOnSecurity Sysmon config
- [ ] Install Sysmon on Domain Controller
- [ ] Install Sysmon on Windows Client
- [ ] Install Splunk on host or dedicated VM
- [ ] Configure Splunk Universal Forwarder on Windows VMs
- [ ] Create Splunk index for Sysmon events
- [ ] Verify Sysmon events appearing in Splunk
- [ ] Download Velociraptor server binary
- [ ] Generate Velociraptor server config
- [ ] Deploy Velociraptor agents to Windows VMs
- [ ] Verify agents checking in to server

## Later (Phase 3: Attack Simulation)
- [ ] Install Empire C2 framework on Kali
- [ ] Create HTTP listener in Empire
- [ ] Generate PowerShell launcher/stager
- [ ] Execute stager on Windows Client (simulate phishing)
- [ ] Verify agent callback to C2
- [ ] Execute reconnaissance commands (whoami, net user, etc.)
- [ ] Execute credential harvesting (Mimikatz module)
- [ ] Perform lateral movement to Domain Controller
- [ ] Simulate data exfiltration
- [ ] Run ransomware simulator
- [ ] Document all attack timestamps

## Later (Phase 4: Detection & Response)
- [ ] Search Splunk for C2 network connections (EventCode=3)
- [ ] Search Splunk for suspicious PowerShell (EventCode=4104)
- [ ] Search Splunk for process creation (EventCode=1)
- [ ] Create Velociraptor hunt for persistence mechanisms
- [ ] Collect triage data with KAPE artifacts
- [ ] Process artifacts with Log2Timeline/Plaso
- [ ] Import timeline into Timesketch
- [ ] Correlate events and build attack timeline

## Later (Phase 5: Forensic Workstation)
- [ ] Download SIFT Workstation OVA
- [ ] Or build custom forensic VM with tool list
- [ ] Install Arsenal Image Mounter
- [ ] Install FTK Imager
- [ ] Install Autopsy
- [ ] Install Eric Zimmerman Tools
- [ ] Install Volatility 3
- [ ] Install CyberChef
- [ ] Practice memory analysis workflow
- [ ] Practice disk artifact analysis workflow

## Done
- [x] Define lab objectives and scope
- [x] Document lab architecture
- [x] Create project documentation structure
- [x] Verify VirtualBox installed (v7.0.26)
- [x] Create internal network (vboxnet0: 192.168.56.1/24, DHCP 100-200)
- [x] Download Kali Linux VM (~/Downloads/DFIR_Lab_ISOs/kali-linux-2025.4-virtualbox-amd64.7z)
- [x] Extract and import Kali Linux VM into VirtualBox (NIC1: vboxnet0, NIC2: NAT)
