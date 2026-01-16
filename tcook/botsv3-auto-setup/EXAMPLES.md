# BOTSv3 Example Search Queries

Example Splunk searches for the Boss of the SOC v3 dataset.

## Basic Queries

### Count all events
```spl
index=botsv3 earliest=0 | stats count
```

### List all sourcetypes with counts
```spl
index=botsv3 earliest=0 | stats count by sourcetype | sort -count
```

### Time range of data
```spl
index=botsv3 earliest=0 | stats min(_time) as earliest max(_time) as latest | eval earliest=strftime(earliest,"%Y-%m-%d %H:%M:%S") | eval latest=strftime(latest,"%Y-%m-%d %H:%M:%S")
```

### Top hosts by event count
```spl
index=botsv3 earliest=0 | stats count by host | sort -count | head 20
```

## Windows Event Logs

### All Windows Security events
```spl
index=botsv3 sourcetype="wineventlog:security" earliest=0 | head 100
```

### Failed logon attempts (EventCode 4625)
```spl
index=botsv3 sourcetype="wineventlog:security" EventCode=4625 earliest=0 | table _time host user src_ip Logon_Type
```

### Successful logons (EventCode 4624)
```spl
index=botsv3 sourcetype="wineventlog:security" EventCode=4624 earliest=0 | stats count by user Logon_Type | sort -count
```

### Process creation (Sysmon EventCode 1)
```spl
index=botsv3 sourcetype="xmlwineventlog:microsoft-windows-sysmon/operational" EventCode=1 earliest=0 | table _time host User Image CommandLine ParentImage
```

### Network connections (Sysmon EventCode 3)
```spl
index=botsv3 sourcetype="xmlwineventlog:microsoft-windows-sysmon/operational" EventCode=3 earliest=0 | table _time host User Image DestinationIp DestinationPort
```

### PowerShell activity
```spl
index=botsv3 sourcetype="wineventlog:microsoft-windows-powershell/operational" earliest=0 | table _time host Message
```

## Network Traffic (Splunk Stream)

### DNS queries
```spl
index=botsv3 sourcetype="stream:dns" earliest=0 | stats count by query | sort -count | head 50
```

### HTTP requests
```spl
index=botsv3 sourcetype="stream:http" earliest=0 | table _time src_ip dest_ip uri http_method status
```

### HTTP requests to suspicious domains
```spl
index=botsv3 sourcetype="stream:http" earliest=0 | stats count by site | sort -count | head 50
```

### HTTP POST requests (potential data exfiltration)
```spl
index=botsv3 sourcetype="stream:http" http_method=POST earliest=0 | table _time src_ip dest_ip site uri http_content_length
```

### SMTP traffic (email)
```spl
index=botsv3 sourcetype="stream:smtp" earliest=0 | table _time src_ip dest_ip sender receiver subject
```

### MySQL queries
```spl
index=botsv3 sourcetype="stream:mysql" earliest=0 | table _time src_ip dest_ip query
```

## AWS CloudTrail

### All AWS API calls
```spl
index=botsv3 sourcetype="aws:cloudtrail" earliest=0 | stats count by eventName | sort -count | head 30
```

### Console logins
```spl
index=botsv3 sourcetype="aws:cloudtrail" eventName=ConsoleLogin earliest=0 | table _time userIdentity.userName sourceIPAddress responseElements.ConsoleLogin
```

### Failed AWS API calls
```spl
index=botsv3 sourcetype="aws:cloudtrail" errorCode=* earliest=0 | stats count by eventName errorCode | sort -count
```

### S3 bucket access
```spl
index=botsv3 sourcetype="aws:cloudtrail" eventSource="s3.amazonaws.com" earliest=0 | stats count by eventName requestParameters.bucketName | sort -count
```

### IAM changes
```spl
index=botsv3 sourcetype="aws:cloudtrail" eventSource="iam.amazonaws.com" earliest=0 | table _time eventName userIdentity.userName requestParameters.*
```

## Cisco ASA Firewall

### All firewall events
```spl
index=botsv3 sourcetype="cisco:asa" earliest=0 | stats count by action | sort -count
```

### Denied connections
```spl
index=botsv3 sourcetype="cisco:asa" action=denied earliest=0 | table _time src_ip dest_ip dest_port protocol
```

### Top denied sources
```spl
index=botsv3 sourcetype="cisco:asa" action=denied earliest=0 | stats count by src_ip | sort -count | head 20
```

## Osquery

### Osquery results
```spl
index=botsv3 sourcetype="osquery:results" earliest=0 | head 100
```

### Listening ports
```spl
index=botsv3 sourcetype="osquery:results" name=listening_ports earliest=0 | spath | table _time host columns.port columns.address columns.pid
```

### Running processes
```spl
index=botsv3 sourcetype="osquery:results" name=processes earliest=0 | spath | table _time host columns.name columns.cmdline columns.uid
```

## Office 365

### O365 management activity
```spl
index=botsv3 sourcetype="o365:management:activity" earliest=0 | stats count by Operation | sort -count
```

### O365 sign-ins
```spl
index=botsv3 sourcetype="ms:aad:signin" earliest=0 | table _time userPrincipalName ipAddress clientAppUsed status.errorCode
```

### Email message traces
```spl
index=botsv3 sourcetype="ms:o365:reporting:messagetrace" earliest=0 | table _time SenderAddress RecipientAddress Subject Status
```

## Symantec Endpoint Protection

### Endpoint security events
```spl
index=botsv3 sourcetype="symantec:ep:*" earliest=0 | stats count by sourcetype | sort -count
```

### Malware detections
```spl
index=botsv3 sourcetype="symantec:ep:risk:file" earliest=0 | table _time host File_Path Actual_Action
```

### Network traffic blocked by endpoint
```spl
index=botsv3 sourcetype="symantec:ep:traffic:file" earliest=0 | table _time host Remote_Host_IP Remote_Port Application
```

## Linux/Unix

### Syslog messages
```spl
index=botsv3 sourcetype="syslog" earliest=0 | stats count by host | sort -count
```

### Authentication events (secure log)
```spl
index=botsv3 sourcetype="linux_secure" earliest=0 | table _time host process message
```

### Linux audit events
```spl
index=botsv3 sourcetype="linux_audit" earliest=0 | table _time host type key
```

### Bash history
```spl
index=botsv3 sourcetype="bash_history" earliest=0 | table _time host _raw
```

## Investigation Queries

### Search for specific IP
```spl
index=botsv3 earliest=0 "10.0.0.1" | stats count by sourcetype | sort -count
```

### Search for specific user
```spl
index=botsv3 earliest=0 user="*admin*" | stats count by sourcetype user | sort -count
```

### Search for base64 encoded strings
```spl
index=botsv3 earliest=0 | regex _raw="[A-Za-z0-9+/]{50,}={0,2}" | table _time sourcetype host _raw
```

### Search for potential command injection
```spl
index=botsv3 earliest=0 ("|" OR ";" OR "`" OR "$(" OR "&&") | stats count by sourcetype | sort -count
```

### Search for encoded PowerShell
```spl
index=botsv3 earliest=0 "powershell" "-enc" OR "-EncodedCommand" | table _time host _raw
```

## Python Client Usage

```bash
# Run these from scripts/python_client directory with venv activated

# Health check
python splunk_client.py health

# Server info
python splunk_client.py info

# List sourcetypes
python splunk_client.py sourcetypes

# Run a search
python splunk_client.py search "index=botsv3 earliest=0 | stats count by sourcetype | head 10"

# Export to JSON
python splunk_client.py export "index=botsv3 sourcetype=aws:cloudtrail | head 1000" -o cloudtrail.json

# Interactive mode
python splunk_client.py interactive
```

## Data Extraction

```bash
# Analyze data
python extract_data.py analyze --index botsv3

# Extract specific sourcetypes to JSONL
python extract_data.py extract -s "wineventlog:security" -s "aws:cloudtrail" --output ./extracted --format jsonl

# Extract to Parquet (recommended for Databricks)
python extract_data.py extract --index botsv3 --output ./extracted --format parquet

# Validate extraction
python extract_data.py validate ./extracted/extraction_manifest.json
```
