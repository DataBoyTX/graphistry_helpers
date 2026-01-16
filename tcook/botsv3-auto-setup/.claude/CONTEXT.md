# Project Context

## Environment
- **Language(s):** Bash (Docker/setup scripts), Python 3.8+ (API client)
- **Runtime:** Docker container (Ubuntu 22.04), Python virtual environment
- **OS / Platform:** Linux (Docker host), Ubuntu 22.04 (container)
- **Deployment target:** Local Docker environment for security training/CTF

## Constraints
- **Performance:** 
  - Minimum 4GB RAM for Splunk container
  - 2+ CPU cores recommended
  - ~10GB disk space (image + dataset)
- **Security:**
  - Self-signed SSL certificates for REST API
  - Default credentials (change in production)
  - Container runs as non-root `splunk` user
- **Compliance:**
  - Splunk Enterprise free trial license (500MB/day indexing limit)
  - BOTSv3 data is pre-indexed, no licensing concerns for historical data
- **Time / scope limits:**
  - First build: 10-20 minutes (downloads ~820MB)
  - Subsequent starts: 2-3 minutes

## Known Assumptions
- Docker and Docker Compose are installed on host system
- Network access available to download Splunk and BOTSv3 dataset
- Ports 8000, 8089, 8088, 9997 are available on host
- Python 3.8+ available for API client (optional)
- User has basic familiarity with Docker and Splunk

## External Systems
- **APIs:**
  - Splunk REST API (https://localhost:8089)
  - HTTP Event Collector (https://localhost:8088)
- **Databases:**
  - Splunk KV Store (internal)
  - Splunk indexes (botsv3 index with pre-loaded data)
- **Third-party services:**
  - Splunk download server (initial build only)
  - AWS S3 for BOTSv3 dataset download (initial build only)

## Open Questions
- Should additional Splunk apps be pre-installed for better field extraction?
- Is there a need for persistent storage across container rebuilds?
- Should HEC tokens be pre-configured for external data ingestion?
