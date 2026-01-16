# Available Tools

## Code Execution
- **Local shell commands:** Full access via bash
- **Docker:** Build, run, compose, logs, exec
- **Python:** 3.8+ with virtual environment
- **Unit test runner:** pytest (if added to requirements)

## External Access
- **Internet:** Allowed for:
  - Splunk download server (download.splunk.com)
  - BOTSv3 dataset (botsdataset.s3.amazonaws.com)
  - Python packages (pypi.org)
- **Package managers:**
  - apt (Ubuntu packages in Docker)
  - pip (Python packages)
  - docker (Container management)

## File Operations
- Read/write within repository
- No destructive deletes without confirmation
- Create directories as needed
- Edit configuration files

## Project-Specific Tools

### Docker Commands
```bash
# Build image
docker build -t splunk-botsv3:latest .

# Run container
docker-compose up -d

# View logs
docker logs -f splunk-botsv3

# Enter container shell
docker exec -it splunk-botsv3 bash

# Stop and remove
docker-compose down

# Clean rebuild
docker-compose down -v
docker build --no-cache -t splunk-botsv3:latest .
```

### Python Client Commands
```bash
# Activate virtual environment
cd python_client
source venv/bin/activate

# Available commands
python splunk_client.py --help
python splunk_client.py info           # Server information
python splunk_client.py health         # Health check
python splunk_client.py indexes        # List indexes
python splunk_client.py sourcetypes    # List BOTSv3 sourcetypes
python splunk_client.py apps           # List installed apps
python splunk_client.py botsv3-stats   # BOTSv3 statistics
python splunk_client.py interactive    # Interactive mode

# Search commands
python splunk_client.py search "index=botsv3 earliest=0 | head 10"
python splunk_client.py search "index=botsv3 sourcetype=wineventlog" -c 50
python splunk_client.py export "index=botsv3 | head 100" -o results.json
```

### Splunk REST API (curl)
```bash
# Server info
curl -sk -u admin:changeme123 https://localhost:8089/services/server/info

# List indexes
curl -sk -u admin:changeme123 https://localhost:8089/services/data/indexes

# Run search
curl -sk -u admin:changeme123 \
  -d "search=search index=botsv3 earliest=0 | head 10" \
  -d "output_mode=json" \
  https://localhost:8089/services/search/jobs/oneshot
```

### Setup Scripts
```bash
# Full automated setup
./scripts/setup.sh

# Build only
./scripts/setup.sh --build-only

# Start only
./scripts/setup.sh --start-only

# Python setup only
./scripts/setup.sh --python-only

# Test connection
./scripts/setup.sh --test
```

### Data Extraction Commands
```bash
# Activate virtual environment first
cd python_client
source venv/bin/activate

# Analyze BOTSv3 data (counts, sourcetypes)
python extract_data.py analyze --index botsv3

# Extract all data (JSONL format, strips Splunk metadata)
python extract_data.py extract --index botsv3 --output ./extracted_data --format jsonl

# Extract with raw field included
python extract_data.py extract --index botsv3 --output ./extracted_data --include-raw

# Extract specific sourcetypes only
python extract_data.py extract -s wineventlog -s "stream:http" --output ./extracted_data

# Extract to Parquet (recommended for Databricks)
python extract_data.py extract --format parquet --output ./extracted_data

# Validate extraction against Splunk counts
python extract_data.py validate ./extracted_data/extraction_manifest.json
```

### Databricks Loading Commands
```bash
# Set environment variables
export DATABRICKS_HOST=your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-access-token
export DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id

# Validate local extraction
python databricks_loader.py validate-local ./extracted_data/extraction_manifest.json

# Load data to Databricks
python databricks_loader.py load ./extracted_data \
    --catalog main --schema botsv3 --overwrite

# Validate Databricks against extraction
python databricks_loader.py validate-databricks ./extracted_data/extraction_manifest.json \
    --output validation_report.json

# Generate comparison report
python databricks_loader.py report ./extracted_data/extraction_manifest.json
```

### End-to-End Testing
```bash
# Run full test suite
python e2e_test.py

# Run without extraction tests (faster)
python e2e_test.py --skip-extraction

# Custom Splunk connection
python e2e_test.py --host localhost --port 8089 --username admin --password changeme123

# Output JSON results
python e2e_test.py --json-output > test_results.json
```

## Usage Rules
- Prefer existing tools over introducing new ones
- Explain why a tool is needed before using it
- Document any new tools in this file
- Test commands before documenting them

## Troubleshooting Tools

### Container Debugging
```bash
# Check container status
docker ps -a

# View container resource usage
docker stats splunk-botsv3

# Inspect container
docker inspect splunk-botsv3

# Check Splunk internal logs
docker exec splunk-botsv3 cat /opt/splunk/var/log/splunk/splunkd.log
```

### Network Debugging
```bash
# Check port bindings
docker port splunk-botsv3

# Test HTTP connectivity
curl -s http://localhost:8000/en-US/account/login

# Test HTTPS API
curl -sk https://localhost:8089/services/server/info
```

### Python Debugging
```bash
# Check installed packages
pip list

# Run with verbose output
python -v splunk_client.py health

# Check environment
python -c "import os; print(os.environ.get('SPLUNK_HOST'))"
```
