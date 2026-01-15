# Architectural & Design Decisions - DFIR Lab

## Decision Log

### 2025-01-12 — Virtualization Platform Selection
**Decision:** Use local hypervisor (VirtualBox/VMware/Hyper-V) rather than cloud
**Reasoning:** Lower cost, no ongoing expenses, full control over network isolation, ability to work offline, faster iteration
**Alternatives Considered:** AWS/Azure VMs, Proxmox cluster, bare metal
**Implications:** Limited by host hardware resources, manual backup management

---

### 2025-01-12 — Windows-Centric Lab Focus
**Decision:** Focus primarily on Windows enterprise environment
**Reasoning:** 95%+ of ransomware incidents involve Windows environments; reflects real-world enterprise reality
**Alternatives Considered:** Linux-only, mixed environment, macOS inclusion
**Implications:** May need to add Linux systems later for cloud/container scenarios

---

### 2025-01-12 — Sysmon for Enhanced Logging
**Decision:** Deploy Sysmon rather than rely solely on native Windows logging
**Reasoning:** Sysmon provides granular visibility (process creation, network connections, file hashes) that native logging lacks; often makes disk forensics unnecessary
**Alternatives Considered:** Native Windows Event Logging only, commercial EDR
**Implications:** Increased log volume, need appropriate Sysmon config tuning

---

### 2025-01-12 — Splunk as SIEM Platform
**Decision:** Use Splunk free tier for log aggregation and analysis
**Reasoning:** Industry-standard tool, free tier sufficient for lab, transferable skills to enterprise environments, extensive community resources
**Alternatives Considered:** Elastic Stack (ELK), Graylog, Azure Sentinel
**Implications:** 500MB/day indexing limit on free tier, may need to manage log retention

---

### 2025-01-12 — Velociraptor for EDR/Forensic Collection
**Decision:** Deploy Velociraptor as primary EDR and forensic collection tool
**Reasoning:** Open source, powerful VQL query language, scalable forensic collection, active development community
**Alternatives Considered:** OSQuery, GRR, commercial EDR trial
**Implications:** Learning curve for VQL, need to maintain server infrastructure

---

### 2025-01-12 — Empire for C2 Simulation
**Decision:** Use Empire framework for command & control simulation
**Reasoning:** Well-documented, PowerShell-based (realistic), generates detectable artifacts for training, active community
**Alternatives Considered:** Cobalt Strike (commercial), Sliver, Metasploit
**Implications:** Empire tactics well-known to defenders, may need additional C2 frameworks for variety

---

### 2025-01-12 — Timesketch for Timeline Analysis
**Decision:** Use Timesketch for collaborative forensic timeline analysis
**Reasoning:** Open source, integrates with Plaso/Log2Timeline, web-based collaboration, Sigma rule support
**Alternatives Considered:** Timeline Explorer, manual Excel analysis, commercial tools
**Implications:** Requires additional infrastructure (Elasticsearch backend)

---

### 2025-01-12 — Internal Network Isolation
**Decision:** Use isolated internal virtual network (192.168.0.X) with no internet access for attack VMs
**Reasoning:** Prevent accidental exposure, contain attack tools, simulate air-gapped investigation
**Alternatives Considered:** NAT with firewall rules, full internet access
**Implications:** May need to manually transfer tools/updates to isolated VMs

---

### 2025-01-12 — Snapshot-Based Recovery Strategy
**Decision:** Use VM snapshots for state preservation and recovery
**Reasoning:** Quick rollback after attacks, preserve known-good states, enable repeatable experiments
**Alternatives Considered:** Full VM cloning, backup to NAS, no backup strategy
**Implications:** Snapshot storage requirements, potential performance impact
