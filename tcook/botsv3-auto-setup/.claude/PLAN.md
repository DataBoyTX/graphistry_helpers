# Project Plan

## Goal
Create a fully automated Docker-based Splunk Enterprise environment pre-loaded with the BOTSv3 (Boss of the SOC v3) dataset for security training, CTF practice, and DFIR skill development. Include a Python CLI tool for programmatic interaction with Splunk's REST API, data extraction capabilities, and Databricks loading/validation.

## Non-Goals
- Production-ready Splunk deployment (this is for training/lab use)
- Installing all 25+ recommended Splunk apps (can be added manually)
- Automated CTF scoring/answer checking
- Multi-node Splunk cluster deployment
- Real-time data ingestion from external sources (dataset is pre-loaded)

## High-Level Phases

### 1. Discovery / Requirements ✅
- [x] Research BOTSv3 dataset requirements
- [x] Identify Splunk version compatibility
- [x] Document required apps and add-ons
- [x] Define Python client capabilities
- [x] Define Databricks export requirements

### 2. Design ✅
- [x] Design Dockerfile for Splunk + BOTSv3
- [x] Design docker-compose configuration
- [x] Design Python REST API client architecture
- [x] Design setup/build scripts
- [x] Design data extraction pipeline
- [x] Design Databricks loading workflow

### 3. Implementation ✅
- [x] Create Dockerfile with multi-stage build
- [x] Create entrypoint script for Splunk initialization
- [x] Create docker-compose.yml
- [x] Create Python CLI client with Click
- [x] Create setup and build scripts
- [x] Create data extraction tool
- [x] Create Databricks loader and validator
- [x] Create end-to-end test suite
- [x] Create project documentation

### 4. Validation / Testing
- [ ] Build Docker image successfully
- [ ] Verify Splunk starts and is accessible
- [ ] Verify BOTSv3 data is searchable
- [ ] Test Python client commands
- [ ] Test data extraction pipeline
- [ ] Test count validation (Splunk vs extracted files)
- [ ] Test schema validation
- [ ] Test Databricks loading (requires Databricks environment)

### 5. Cleanup / Documentation
- [ ] Review and clean up code
- [ ] Add inline documentation
- [ ] Create usage examples
- [ ] Document troubleshooting steps
- [ ] Document Databricks loading process

## Current Phase
**Phase:** 4 - Validation / Testing

## Success Criteria
- [x] Docker image builds without errors
- [ ] Splunk Web UI accessible at http://localhost:8000
- [ ] REST API accessible at https://localhost:8089
- [ ] Search `index=botsv3 earliest=0` returns events
- [ ] Python client can execute searches and display results
- [ ] Setup script completes without manual intervention
- [ ] All sourcetypes from BOTSv3 dataset are present
- [ ] Data extraction produces valid JSONL/Parquet files
- [ ] Extracted event counts match Splunk counts per sourcetype
- [ ] Splunk internal metadata fields are stripped from exports
- [ ] Databricks tables load successfully (when configured)
- [ ] Databricks counts match extracted counts

## Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| Project structure created | Day 1 | ✅ Complete |
| Dockerfile working | Day 1 | ✅ Complete |
| Python client functional | Day 1 | ✅ Complete |
| Data extraction tools | Day 1 | ✅ Complete |
| Databricks integration | Day 1 | ✅ Complete |
| End-to-end testing | Day 1-2 | 🔄 In Progress |
| Documentation complete | Day 2 | 🔄 In Progress |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Download failures | Medium | High | Add retry logic, checksum verification |
| Memory issues | Medium | Medium | Document minimum requirements, health checks |
| App compatibility | Low | Medium | Use newer Splunk version, test field extractions |
| SSL issues | Low | Low | Disable verification in clients, document |
| Databricks auth issues | Medium | Medium | Clear documentation, env variable support |
| Data type conversion | Medium | Medium | Flexible type handling, validation checks |
