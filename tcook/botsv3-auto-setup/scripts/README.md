# Splunk BOTSv3 Docker

Automated Docker deployment of Splunk Enterprise with the Boss of the SOC v3 (BOTSv3) dataset for security training, CTF practice, and DFIR skill development.

## Overview

This project provides:
- **Dockerized Splunk Enterprise** 9.1.0.2 with BOTSv3 dataset pre-loaded
- **Python CLI client** for REST API interaction
- **Automated setup scripts** for one-command deployment

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 4GB+ RAM available for container
- ~10GB disk space
- Python 3.8+ (optional, for CLI client)

### One-Command Setup

```bash
./scripts/setup.sh
```

This will:
1. Build the Docker image (~10-15 minutes first time)
2. Start the Splunk container
3. Wait for Splunk to initialize
4. Set up the Python client
5. Run connection tests

### Manual Setup

```bash
# Build the Docker image
docker build -t splunk-botsv3:latest .

# Start with docker-compose
docker-compose up -d

# Wait for Splunk to start (2-3 minutes)
docker logs -f splunk-botsv3
```

## Access

| Service | URL | Credentials |
|---------|-----|-------------|
| Splunk Web UI | http://localhost:8000 | admin / changeme123 |
| Splunk REST API | https://localhost:8089 | admin / changeme123 |

## BOTSv3 Dataset

The BOTSv3 dataset contains security event data for CTF-style challenges. Access it with:

```spl
index=botsv3 earliest=0
```

### Included Sourcetypes

The dataset includes 70+ sourcetypes:
- Windows Event Logs (`wineventlog`, `xmlwineventlog`)
- Sysmon (`xmlwineventlog:microsoft-windows-sysmon/operational`)
- Network traffic (`stream:http`, `stream:dns`, `stream:tcp`)
- AWS logs (`aws:cloudtrail`, `aws:cloudwatch`, `aws:s3:accesslogs`)
- Symantec Endpoint (`symantec:ep:*`)
- Linux logs (`linux_audit`, `linux_secure`, `syslog`)
- And many more...

## Python CLI Client

### Setup

```bash
cd python_client
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Usage

```bash
# Server information
python splunk_client.py info

# Health check
python splunk_client.py health

# List indexes
python splunk_client.py indexes

# List BOTSv3 sourcetypes
python splunk_client.py sourcetypes

# Execute search
python splunk_client.py search "index=botsv3 | head 10"

# Search with options
python splunk_client.py search "index=botsv3 sourcetype=wineventlog" -c 100 --json-output

# BOTSv3 statistics
python splunk_client.py botsv3-stats

# Interactive mode
python splunk_client.py interactive

# Export results
python splunk_client.py export "index=botsv3 | head 1000" -o results.json
```

### Connection Options

```bash
python splunk_client.py --host localhost --port 8089 --username admin --password changeme123 info
```

Or set environment variables:
```bash
export SPLUNK_HOST=localhost
export SPLUNK_PORT=8089
export SPLUNK_USERNAME=admin
export SPLUNK_PASSWORD=changeme123
```

## Docker Management

```bash
# Start container
docker-compose up -d

# Stop container
docker-compose down

# View logs
docker logs -f splunk-botsv3

# Enter container shell
docker exec -it splunk-botsv3 bash

# Restart Splunk inside container
docker exec splunk-botsv3 /opt/splunk/bin/splunk restart

# Clean restart (remove volumes)
docker-compose down -v
docker-compose up -d
```

## Data Extraction (for Databricks)

The extraction tool exports BOTSv3 data from Splunk, strips internal metadata, and prepares it for loading into Databricks.

### Extract Data

```bash
cd python_client
source venv/bin/activate

# Analyze what's available
python extract_data.py analyze --index botsv3

# Extract all sourcetypes to JSONL (recommended)
python extract_data.py extract --index botsv3 --output ./extracted_data --format jsonl

# Extract to Parquet (best for Databricks)
python extract_data.py extract --index botsv3 --output ./extracted_data --format parquet

# Extract specific sourcetypes only
python extract_data.py extract -s wineventlog -s "stream:http" --output ./extracted_data
```

### Stripped Splunk Metadata Fields

The following internal Splunk fields are automatically removed during extraction:

| Field | Description |
|-------|-------------|
| `_bkt`, `_cd`, `_si` | Index bucket metadata |
| `_indextime`, `_subsecond` | Indexing timestamps |
| `splunk_server` | Server routing info |
| `punct`, `linecount` | Parsing metadata |
| `_kv`, `_eventtype_color` | Search-time metadata |

### Field Renaming

Fields are renamed for Databricks compatibility:

| Splunk Field | Databricks Field |
|--------------|------------------|
| `_time` | `event_time` |
| `host` | `src_host` |
| `source` | `log_source` |
| `sourcetype` | `source_type` |

### Extraction Manifest

Each extraction generates a manifest file (`extraction_manifest.json`) containing:
- Event counts per sourcetype
- Field lists per sourcetype
- File checksums (MD5)
- Validation status

## Databricks Loading

### Prerequisites

```bash
pip install databricks-sql-connector databricks-sdk pandas pyarrow
```

### Environment Variables

```bash
export DATABRICKS_HOST=your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-access-token
export DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
```

### Load Data

```bash
# Load extracted data to Databricks
python databricks_loader.py load ./extracted_data \
    --catalog main --schema botsv3 --overwrite

# Validate counts match
python databricks_loader.py validate-databricks ./extracted_data/extraction_manifest.json
```

### Validation Pipeline

The full validation pipeline ensures data integrity:

```
Splunk → Extract (JSONL/Parquet) → Load to Databricks → Validate
         ↓                         ↓
    Count Check                Count Check
    Schema Check               Schema Check
```

## End-to-End Testing

Run the complete validation suite:

```bash
python e2e_test.py

# Output:
# ✓ Splunk Connection
# ✓ Splunk Authentication  
# ✓ BOTSv3 Index Exists
# ✓ BOTSv3 Has Data
# ✓ Sourcetype Counts
# ✓ Sample Searches
# ✓ Field Extraction
# ✓ Data Extraction
# ✓ Count Validation
# ✓ Schema Consistency
```

## Project Structure

```
splunk-botsv3-docker/
├── .claude/                 # Claude workspace documentation
│   ├── CONTEXT.md          # Project context and constraints
│   ├── DECISIONS.md        # Architectural decisions
│   ├── PLAN.md             # Project plan and milestones
│   ├── README.md           # Workspace overview
│   ├── SYSTEM.md           # Claude operating instructions
│   ├── TODO.md             # Task tracking
│   └── TOOLS.md            # Available tools
├── python_client/           # Python REST API client
│   ├── splunk_client.py    # Main CLI application
│   ├── extract_data.py     # Data extraction tool
│   ├── databricks_loader.py # Databricks loader/validator
│   ├── e2e_test.py         # End-to-end test suite
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment template
├── scripts/                 # Build and setup scripts
│   ├── build.sh            # Docker build script
│   ├── entrypoint.sh       # Container entrypoint
│   └── setup.sh            # Complete setup script
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
└── README.md               # This file
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| SPLUNK_PASSWORD | changeme123 | Admin password |
| SPLUNK_USER | admin | Admin username |
| SPLUNK_HOST | localhost | Splunk hostname |
| SPLUNK_PORT | 8089 | REST API port |

### Ports

| Port | Service |
|------|---------|
| 8000 | Splunk Web UI |
| 8089 | REST API (splunkd) |
| 9997 | Forwarder receiving |
| 8088 | HTTP Event Collector |

## Troubleshooting

### Container won't start

```bash
# Check for port conflicts
lsof -i :8000
lsof -i :8089

# Check container logs
docker logs splunk-botsv3

# Check resource usage
docker stats
```

### Can't connect to REST API

```bash
# Test connectivity
curl -sk https://localhost:8089/services/server/info

# Check SSL certificate
openssl s_client -connect localhost:8089 </dev/null

# Try with explicit credentials
curl -sk -u admin:changeme123 https://localhost:8089/services/server/info
```

### No data in BOTSv3 index

```bash
# Check if index exists
curl -sk -u admin:changeme123 https://localhost:8089/services/data/indexes/botsv3

# Check event count
curl -sk -u admin:changeme123 \
  -d "search=search index=botsv3 earliest=0 | stats count" \
  -d "output_mode=json" \
  https://localhost:8089/services/search/jobs/oneshot
```

### Python client errors

```bash
# Check dependencies
pip list | grep -E "requests|click|rich"

# Test basic connectivity
python -c "import requests; print(requests.get('http://localhost:8000', timeout=5).status_code)"

# Enable debug logging
python splunk_client.py --help
```

## Security Notice

⚠️ **This is a lab/training environment.** Default credentials are used for convenience.

For any shared or production use:
1. Change the default password
2. Enable SSL certificate verification
3. Do not expose ports to public networks
4. Review Splunk security best practices

## Resources

- [BOTSv3 GitHub Repository](https://github.com/splunk/botsv3)
- [Splunk REST API Reference](https://docs.splunk.com/Documentation/Splunk/latest/RESTREF/RESTprolog)
- [Splunk Search Reference](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference)
- [Boss of the SOC](https://bots.splunk.com/)

## License

- **BOTSv3 Dataset:** CC0 Public Domain
- **This Project:** MIT License
- **Splunk Enterprise:** Splunk EULA (free trial)
