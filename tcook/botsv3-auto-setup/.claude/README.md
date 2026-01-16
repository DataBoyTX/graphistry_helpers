# .claude Workspace

This folder contains lightweight, persistent state files intended for use by Claude (or any coding agent) when working on the Splunk BOTSv3 Docker project.

## Suggested Operating Practice

1. **Read SYSTEM.md first** - Contains operating principles and workflow rules
2. **Use PLAN.md to maintain direction** - Check current phase and success criteria
3. **Only execute tasks listed in TODO.md → Now** - Stay focused on current work
4. **Record architectural choices in DECISIONS.md** - Document why decisions were made
5. **Keep CONTEXT.md updated** - As assumptions or constraints change

## File Purposes

| File | Purpose |
|------|---------|
| CONTEXT.md | Environment, constraints, assumptions, external systems |
| DECISIONS.md | Architectural and design decisions with rationale |
| PLAN.md | Project goals, phases, milestones, success criteria |
| README.md | This file - workspace overview |
| SYSTEM.md | Operating principles and workflow rules for Claude |
| TODO.md | Task tracking - Now, Next, Later, Done |
| TOOLS.md | Available tools and usage guidelines |

## Quick Reference

### Project: Splunk BOTSv3 Docker

**Goal:** Automated Docker setup for Splunk Enterprise with BOTSv3 dataset

**Current Phase:** Validation / Testing

**Key Commands:**
```bash
# Build and setup everything
./scripts/setup.sh

# Python client
cd python_client
source venv/bin/activate
python splunk_client.py --help

# Docker management
docker-compose up -d
docker-compose down
docker logs -f splunk-botsv3
```

**Access Points:**
- Splunk Web: http://localhost:8000
- REST API: https://localhost:8089
- Credentials: admin / changeme123
