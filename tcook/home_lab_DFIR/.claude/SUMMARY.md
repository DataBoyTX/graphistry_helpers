# DFIR Attack & Defend Lab - Project Summary

## Project Goal
Build a simulated enterprise environment for practicing Digital Forensics and Incident Response (DFIR) skills, including attack execution, log analysis, and forensic investigation.

## Current Status
**Phase:** 1 of 5 - Foundation Infrastructure
**Last Updated:** 2026-01-14

---

## Completed Work

### Documentation & Planning
- [x] Defined lab objectives and scope
- [x] Documented lab architecture and network diagram
- [x] Created project documentation structure (`.claude/` folder)
- [x] Recorded architectural decisions (virtualization, tooling choices)
- [x] Established tool inventory for defensive and offensive operations

### Infrastructure Setup
- [x] Verified VirtualBox installed (v7.0.26)
- [x] Created internal host-only network:
  - Network: `vboxnet0`
  - Subnet: `192.168.56.0/24`
  - Gateway: `192.168.56.1`
  - DHCP Range: `192.168.56.100-200`

### Virtual Machines
- [x] Downloaded Kali Linux VM (`kali-linux-2025.4-virtualbox-amd64.7z`)
- [x] Extracted and imported Kali Linux into VirtualBox
- [x] Configured Kali networking:
  - NIC1: Host-only (vboxnet0) - internal lab network
  - NIC2: NAT - internet access for updates/tools

---

## In Progress

### Phase 1 - Foundation (Current)
- [ ] Download Windows Server 2022 evaluation ISO
- [ ] Download Windows 10 Enterprise evaluation ISO
- [ ] Create Windows Server VM (4GB RAM, 60GB disk)
- [ ] Install and promote to Domain Controller
- [ ] Create Windows Client VM (4GB RAM, 40GB disk)
- [ ] Join client to domain
- [ ] Create test user accounts (alice, bob, admin)
- [ ] Take baseline snapshots

---

## Upcoming Phases

### Phase 2 - Defensive Tooling
- PowerShell logging via GPO (Module, ScriptBlock, Transcription)
- Sysmon deployment with SwiftOnSecurity config
- Splunk installation and log forwarding
- Velociraptor server and agent deployment

### Phase 3 - Attack Simulation
- Empire C2 framework setup
- Simulated ransomware attack chain execution
- Attack timestamp documentation

### Phase 4 - Detection & Response
- Splunk-based threat hunting
- Velociraptor forensic hunts
- KAPE artifact collection
- Timeline generation with Plaso/Timesketch

### Phase 5 - Forensic Workstation
- SIFT or custom forensic VM
- Forensic tool suite installation
- Artifact analysis workflow practice

---

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hypervisor | VirtualBox | Free, cross-platform, full control |
| Focus | Windows-centric | Reflects 95%+ of ransomware targets |
| Enhanced Logging | Sysmon | Granular visibility beyond native logging |
| SIEM | Splunk (free tier) | Industry standard, transferable skills |
| EDR | Velociraptor | Open source, powerful VQL queries |
| C2 Framework | Empire | Well-documented, realistic artifacts |
| Timeline Analysis | Timesketch | Open source, Plaso integration |
| Network | Isolated 192.168.56.0/24 | Prevent accidental exposure |

---

## Network Architecture

```
┌─────────────────────────────────────────────────────┐
│           Virtual Guest Environment                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │  Kali   │    │ Win 10  │    │   DC    │         │
│  │ Attack  │    │ Client  │    │ Server  │         │
│  │   [x]   │    │   [ ]   │    │   [ ]   │         │
│  └────┬────┘    └────┬────┘    └────┬────┘         │
│       │              │              │               │
│       └──────────────┴──────────────┘               │
│           Internal Network: 192.168.56.0/24         │
└─────────────────────────────────────────────────────┘
```

---

## Resources

- Blue Cape Security Lab Guide: https://bluecapesecurity.com/build-your-lab/
- Attack Tutorial: https://bluecapesecurity.com/attack-and-defend-your-lab/
- Forensic Workstation Guide: https://bluecapesecurity.com/build-your-forensic-workstation/
- DFIR Discord: https://tinyurl.com/dfir-discord
- Splunk BOTS Dataset: https://github.com/splunk/botsv3

---

## Files in This Project

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Entry point, directs to .claude/ folder |
| `.claude/README.md` | Project overview and operating practice |
| `.claude/PLAN.md` | High-level phases and success criteria |
| `.claude/TODO.md` | Task tracking by phase |
| `.claude/CONTEXT.md` | Environment, constraints, assumptions |
| `.claude/SYSTEM.md` | Claude assistant operating guidelines |
| `.claude/TOOLS.md` | Approved defensive and offensive tools |
| `.claude/DECISIONS.md` | Architectural decision log |
| `.claude/SUMMARY.md` | This file - project state summary |
