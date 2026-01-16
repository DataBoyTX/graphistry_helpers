#!/bin/bash
# Entrypoint script for Splunk Enterprise container

set -e

SPLUNK_HOME=${SPLUNK_HOME:-/opt/splunk}
SPLUNK_CMD="${SPLUNK_HOME}/bin/splunk"

# Function to start Splunk
start_splunk() {
    echo "Starting Splunk Enterprise..."
    
    # Check if this is first run
    if [ ! -f "${SPLUNK_HOME}/.first_run_complete" ]; then
        echo "First run detected. Initializing Splunk..."
        
        # Start Splunk for the first time with license acceptance
        ${SPLUNK_CMD} start --accept-license --answer-yes --no-prompt
        
        # Wait for Splunk to be ready
        echo "Waiting for Splunk to initialize..."
        sleep 30
        
        # Create marker file
        touch "${SPLUNK_HOME}/.first_run_complete"
        
        echo "First run initialization complete."
    else
        echo "Starting Splunk (subsequent run)..."
        ${SPLUNK_CMD} start --accept-license --answer-yes --no-prompt
    fi
    
    # Keep container running and tail logs
    echo "Splunk started successfully!"
    echo "============================================"
    echo "Splunk Web UI: http://localhost:8000"
    echo "Splunk REST API: https://localhost:8089"
    echo "Username: ${SPLUNK_USER:-admin}"
    echo "Password: ${SPLUNK_PASSWORD:-changeme123}"
    echo "============================================"
    echo "BOTSv3 Search: index=botsv3 earliest=0"
    echo "============================================"
    
    # Tail the splunkd log to keep container running
    tail -f ${SPLUNK_HOME}/var/log/splunk/splunkd.log
}

# Function to stop Splunk gracefully
stop_splunk() {
    echo "Stopping Splunk..."
    ${SPLUNK_CMD} stop
}

# Trap signals for graceful shutdown
trap stop_splunk SIGTERM SIGINT

# Parse command
case "${1}" in
    start)
        start_splunk
        ;;
    stop)
        stop_splunk
        ;;
    restart)
        stop_splunk
        sleep 5
        start_splunk
        ;;
    status)
        ${SPLUNK_CMD} status
        ;;
    bash|shell)
        exec /bin/bash
        ;;
    *)
        # If no command specified, start Splunk
        start_splunk
        ;;
esac
