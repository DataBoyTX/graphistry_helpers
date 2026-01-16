# TODO

## Now
- [ ] Build Docker image and verify successful completion
- [ ] Test Splunk startup and web UI accessibility
- [ ] Verify BOTSv3 data is searchable (`index=botsv3 earliest=0`)
- [ ] Test Python client connection and basic commands
- [ ] Run end-to-end validation test suite

## Next
- [ ] Test all Python client commands (search, info, health, indexes, sourcetypes)
- [ ] Verify all 70+ sourcetypes are present in BOTSv3 index
- [ ] Test interactive search mode
- [ ] Test data extraction with multiple formats (JSON, JSONL, Parquet)
- [ ] Validate extracted counts match Splunk counts for ALL sourcetypes
- [ ] Verify Splunk internal fields are stripped correctly
- [ ] Test schema/column extraction accuracy
- [ ] Create example search queries for common BOTSv3 questions

## Later (Databricks Integration)
- [ ] Configure Databricks connection (host, token, warehouse)
- [ ] Test Databricks schema creation
- [ ] Load extracted data to Databricks tables
- [ ] Run count validation: Splunk → Extract → Databricks
- [ ] Run schema validation: compare columns at each stage
- [ ] Document data type mapping issues and solutions
- [ ] Create Databricks-specific notebooks for analysis
- [ ] Add Delta Lake support for efficient storage

## Later (Enhancements)
- [ ] Add option to install recommended Splunk apps during build
- [ ] Create script to verify field extractions
- [ ] Add Jupyter notebook support for data exploration
- [ ] Create Docker image for ARM architecture (Apple Silicon)
- [ ] Add CI/CD pipeline for automated testing
- [ ] Consider adding Splunk Enterprise Security (ES) app
- [ ] Add pre-built saved searches for common IOC hunting
- [ ] Add parallel extraction for faster processing
- [ ] Add incremental extraction support

## Done
- [x] Research BOTSv3 requirements from GitHub
- [x] Create project directory structure
- [x] Create Dockerfile for Splunk Enterprise 9.1.0.2
- [x] Create entrypoint.sh script
- [x] Create docker-compose.yml
- [x] Create Python REST API client with Click CLI
- [x] Create requirements.txt for Python dependencies
- [x] Create .env.example for configuration
- [x] Create build.sh script
- [x] Create setup.sh comprehensive setup script
- [x] Create CONTEXT.md with project context
- [x] Create DECISIONS.md with architectural decisions
- [x] Create PLAN.md with project plan
- [x] Create README.md for .claude workspace
- [x] Create SYSTEM.md with Claude instructions
- [x] Create TODO.md (this file)
- [x] Create TOOLS.md with available tools
- [x] Create extract_data.py for Splunk data extraction
- [x] Create databricks_loader.py for Databricks loading
- [x] Create e2e_test.py for end-to-end validation
- [x] Define Splunk internal fields to strip
- [x] Add manifest generation for extraction tracking
- [x] Add count validation between Splunk and extracts
- [x] Add schema comparison utilities

## Blocked
- None currently

## Notes
- Build requires ~820MB download (Splunk + BOTSv3 dataset)
- First startup takes 2-3 minutes for Splunk initialization
- Some field extractions may require installing additional apps
- Databricks integration requires: databricks-sql-connector, databricks-sdk
- Full extraction of all 70+ sourcetypes may take 10-30 minutes
- Parquet format recommended for Databricks (better compression, schema preservation)
