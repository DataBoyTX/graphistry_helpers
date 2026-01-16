# Architectural & Design Decisions

## Decision Log

### 2025-01-15 — Use Splunk 9.1.0.2 Instead of 7.1.7
**Decision:** Use Splunk Enterprise 9.1.0.2 instead of the documented 7.1.7
**Reasoning:** 
- BOTSv3 documentation specifies 7.1.7, but newer versions provide security fixes
- Pre-indexed data format is forward-compatible with newer Splunk versions
- Splunk 9.x has better REST API features and performance
**Alternatives Considered:** Splunk 7.1.7 (documented), 8.x series
**Implications:** 
- Some older apps may have compatibility warnings
- Field extractions should still work
- May need to update some app versions if issues arise

---

### 2025-01-15 — Ubuntu 22.04 Base Image
**Decision:** Use Ubuntu 22.04 LTS as Docker base image
**Reasoning:**
- Long-term support until 2027
- Splunk officially supports Ubuntu 22.04
- Familiar package management (apt)
- Good balance of stability and modern packages
**Alternatives:** Ubuntu 20.04, Debian, CentOS/Rocky, Alpine
**Implications:** Larger image size than Alpine, but better compatibility

---

### 2025-01-15 — Skip App Installation in Initial Build
**Decision:** Only install Splunk and BOTSv3 dataset, skip recommended apps
**Reasoning:**
- BOTSv3 data is pre-indexed with field extractions
- Apps add significant complexity and download time
- Core CTF functionality works without additional apps
- Apps can be added manually if needed for specific questions
**Alternatives:** Install all 25+ recommended apps during build
**Implications:** 
- Some field extractions may be missing
- CIM compliance checks won't work
- Can be remediated by adding apps later

---

### 2025-01-15 — Python Click Framework for CLI
**Decision:** Use Click + Rich for Python CLI client
**Reasoning:**
- Click provides robust argument parsing and subcommands
- Rich provides beautiful terminal output and tables
- Both are well-maintained and widely used
- Good documentation and examples available
**Alternatives:** argparse (stdlib), Typer, Fire
**Implications:** Additional dependencies, but better UX

---

### 2025-01-15 — Self-Signed SSL for REST API
**Decision:** Use Splunk's default self-signed certificates
**Reasoning:**
- Local development environment
- Simplifies setup (no cert management)
- Python client configured to skip verification
**Alternatives:** Generate custom certs, use Let's Encrypt, disable SSL
**Implications:** 
- Security warnings in browsers
- Need to disable SSL verification in clients

---

### 2025-01-15 — Docker Volumes for Persistence
**Decision:** Use named Docker volumes for optional data persistence
**Reasoning:**
- Allows quick restart without losing configuration changes
- Pre-loaded data remains available across restarts
- Can be removed for fresh start
**Alternatives:** Bind mounts, no persistence
**Implications:** More complex cleanup, need to remove volumes for clean state

---

### 2025-01-15 — Default Credentials in Environment Variables
**Decision:** Use environment variables for credentials with sensible defaults
**Reasoning:**
- Easy to change via docker-compose.yml or .env file
- Defaults work out-of-box for testing
- Standard pattern for containerized apps
**Alternatives:** Require credentials at runtime, use secrets management
**Implications:** 
- Default credentials are insecure for production
- Users must change for any shared/production use

---

### 2025-01-15 — JSONL as Default Extraction Format
**Decision:** Use JSONL (JSON Lines) as the default extraction format
**Reasoning:**
- Streaming-friendly (can process line by line)
- Human-readable for debugging
- Widely supported by data tools
- Easy to convert to other formats
**Alternatives:** JSON (single array), Parquet, CSV
**Implications:**
- Larger file sizes than Parquet
- No built-in schema enforcement
- Recommend Parquet for Databricks production use

---

### 2025-01-15 — Strip Splunk Internal Fields by Default
**Decision:** Remove Splunk internal fields (_bkt, _cd, _si, etc.) during extraction
**Reasoning:**
- Internal fields are Splunk-specific metadata not useful in Databricks
- Reduces data size by ~20-30%
- Cleaner schema for analytics
- Preserves data content while removing infrastructure details
**Alternatives:** Keep all fields, make stripping optional per-field
**Implications:**
- Cannot reconstruct exact Splunk event representation
- Some debugging scenarios may want internal fields (--keep-internal flag available)

---

### 2025-01-15 — Rename _time to event_time
**Decision:** Rename _time field to event_time in exports
**Reasoning:**
- Databricks/Spark don't like leading underscores
- More descriptive field name
- Consistent with common data warehouse conventions
**Alternatives:** Keep _time, use backticks in queries
**Implications:**
- Queries must use new field name
- Rename mapping is documented and configurable

---

### 2025-01-15 — Generate Extraction Manifest
**Decision:** Generate a manifest file for each extraction with counts, checksums, and schema
**Reasoning:**
- Enables validation at each pipeline stage
- Provides audit trail for data movement
- Allows resumption of failed extractions
- Essential for count validation between systems
**Alternatives:** No manifest (trust the files), database tracking
**Implications:**
- Extra file per extraction
- Must keep manifest synchronized with data files
