# Project Plan - DFIR Attack & Defend Lab

## Goal
Build an Attack & Defend Home Lab that simulates a realistic enterprise environment for practicing DFIR skills, with the following objectives:

1. Acquire foundational knowledge of enterprise environments
2. Understand and utilize attack tools, frameworks, and infrastructures
3. Develop expertise in detecting and analyzing attack techniques
4. Improve telemetry for better visibility and detection engineering

## Non-Goals
- Production-grade high availability
- Multi-site replication
- Real malware execution (use simulators)
- Internet-facing services
- Compliance certification (this is a learning environment)

## High-Level Phases

### Phase 1: Foundation Infrastructure
- Set up hypervisor environment
- Create Windows Server VM and promote to Domain Controller
- Create Windows Client VM and join to domain
- Create Kali Linux attack VM
- Configure internal networking (192.168.0.X)

### Phase 2: Defensive Tooling
- Enable PowerShell ScriptBlock logging via GPO
- Install and configure Sysmon with appropriate config
- Deploy Splunk and configure log forwarding
- Deploy Velociraptor server and agents
- Validate log collection and visibility

### Phase 3: Attack Execution
- Set up Empire C2 framework on Kali
- Execute simulated attack chain (ransomware lifecycle):
  - Initial access (phishing simulation)
  - Post-exploitation foothold
  - Reconnaissance and credential harvesting
  - Lateral movement
  - Data exfiltration
  - Ransomware simulation
- Document all attack timestamps and techniques

### Phase 4: Incident Response & Analysis
- Use Splunk for initial compromise identification
- Deploy Velociraptor hunts for forensic triage
- Collect forensic artifacts (KAPE targets)
- Process with Plaso/Log2Timeline
- Analyze in Timesketch

### Phase 5: Forensic Workstation
- Build dedicated forensic analysis VM (SIFT or custom)
- Install forensic tool suite
- Practice artifact analysis workflow
- Document findings and create timeline

## Current Phase
**Phase:** 1 - Foundation Infrastructure

## Success Criteria
- [ ] Domain Controller operational with Active Directory
- [ ] Windows client successfully joined to domain
- [ ] Kali Linux can reach internal network
- [ ] Sysmon logging captured in Splunk
- [ ] PowerShell ScriptBlock logging enabled
- [ ] Velociraptor agents reporting to server
- [ ] Successfully execute and detect C2 beacon
- [ ] Generate forensic timeline from attack artifacts
- [ ] Complete ransomware lifecycle simulation with full detection
