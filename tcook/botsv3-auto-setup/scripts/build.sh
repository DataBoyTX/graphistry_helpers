#!/bin/bash
# Build script for Splunk BOTSv3 Docker image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Dockerfile is in the scripts directory
cd "$SCRIPT_DIR"

echo "============================================"
echo "Building Splunk BOTSv3 Docker Image"
echo "============================================"
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    exit 1
fi

# Build options
BUILD_ARGS=""
NO_CACHE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "Building Docker image..."
echo ""

docker build $NO_CACHE -t splunk-botsv3:latest .

echo ""
echo "============================================"
echo "Build Complete!"
echo "============================================"
echo ""
echo "Image: splunk-botsv3:latest"
echo ""
echo "To run the container:"
echo "  docker run -d -p 8000:8000 -p 8089:8089 --name splunk-botsv3 splunk-botsv3:latest"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose up -d"
echo ""
