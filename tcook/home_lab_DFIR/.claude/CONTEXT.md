# Project Context - DFIR Attack & Defend Lab

## Environment
- **Hypervisor:** VirtualBox / VMware / Hyper-V (choose based on host OS)
- **Host OS:** Windows/Linux/macOS (physical machine)
- **Guest VMs:**
  - Windows Server 2019/2022 (Domain Controller)
  - Windows 10/11 (Client workstation)
  - Kali Linux (Attack VM)
  - Ubuntu/SIFT Workstation (Forensic analysis)
- **Network:** Internal network segment (192.168.56.X - vboxnet0)
- **Deployment target:** Local virtualized lab environment

## Hardware Requirements
- **RAM:** Minimum 16GB (32GB+ recommended)
- **Storage:** 200GB+ SSD (for VMs and log storage)
- **CPU:** 4+ cores with virtualization support (VT-x/AMD-V)

## Constraints
- **Performance:** Lab must run on consumer hardware
- **Security:** Isolated from production/home network
- **Storage:** Sysmon and Splunk generate significant log volume
- **Licensing:** Use evaluation/free versions where possible
- **Time/scope:** Phased implementation approach

## Known Assumptions
- Active Directory is the primary identity management system
- Windows environments represent 95%+ of enterprise ransomware cases
- Sysmon provides superior logging over native Windows logging
- Log retention period determined by available storage
- C2 frameworks will be used in isolated environment only

## External Systems / Dependencies
- **SIEM:** Splunk (free tier or dev license)
- **EDR:** Velociraptor (open source)
- **Timeline Analysis:** Timesketch (open source)
- **Log Processing:** Plaso/Log2Timeline
- **C2 Framework:** Empire (for attack simulation)

## Network Architecture
```
┌─────────────────────────────────────────────────┐
│           Virtual Guest Environment              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐     │
│  │  Kali   │    │ Win 10  │    │   DC    │     │
│  │ Attack  │    │ Client  │    │ Server  │     │
│  └────┬────┘    └────┬────┘    └────┬────┘     │
│       │              │              │           │
│       └──────────────┴──────────────┘           │
│              Internal Network                    │
│              192.168.0.X                        │
└─────────────────────────────────────────────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────────────────────────────────────────┐
│           Host Environment                       │
│  ┌──────────┐  ┌────────────┐  ┌─────────┐     │
│  │Velocirap.│  │   Splunk   │  │Timesketch│    │
│  └──────────┘  └────────────┘  └─────────┘     │
└─────────────────────────────────────────────────┘
```

## Open Questions
- Cloud vs local deployment for SIEM components?
- Full disk encryption for forensic workstation?
- Backup strategy for VM snapshots?
- Integration with threat intelligence feeds?
