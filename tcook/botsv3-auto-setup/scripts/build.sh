#!/bin/bash
# Build script for Splunk BOTSv3 Docker image
# Includes all required add-ons for proper field extraction

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESOURCES_DIR="$PROJECT_DIR/resources"
ADDONS_SRC="$RESOURCES_DIR/splunk-add-ons"
ADDONS_DEST="$SCRIPT_DIR/splunk-add-ons"

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
NO_CACHE=""
SKIP_ADDONS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --skip-addons)
            SKIP_ADDONS="yes"
            shift
            ;;
        --check-addons)
            echo "Checking for required add-ons..."
            bash "$SCRIPT_DIR/download_addons.sh" "$ADDONS_SRC"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Prepare add-ons for Docker build context
echo "Preparing Splunk add-ons..."
mkdir -p "$ADDONS_DEST"

if [ "$SKIP_ADDONS" != "yes" ]; then
    # Check if add-ons tarball exists and extract if needed
    if [ -f "$RESOURCES_DIR/splunk-add-ons-for-botsv3.tgz" ]; then
        echo "  Extracting pre-bundled add-ons..."
        tar -xzf "$RESOURCES_DIR/splunk-add-ons-for-botsv3.tgz" -C "$RESOURCES_DIR/" 2>/dev/null || true
    fi

    # Copy add-ons to build context
    if [ -d "$ADDONS_SRC" ] && [ "$(ls -A $ADDONS_SRC 2>/dev/null)" ]; then
        echo "  Copying add-ons to build context..."
        cp -r "$ADDONS_SRC"/*.tgz "$ADDONS_DEST/" 2>/dev/null || true
        ADDON_COUNT=$(ls -1 "$ADDONS_DEST"/*.tgz 2>/dev/null | wc -l)
        echo "  Found $ADDON_COUNT add-on(s)"
    else
        echo "  WARNING: No add-ons found in $ADDONS_SRC"
        echo "  Some field extractions may not work correctly."
        echo "  Run './build.sh --check-addons' to see missing add-ons."
        # Create empty directory for Docker COPY
        touch "$ADDONS_DEST/.gitkeep"
    fi
else
    echo "  Skipping add-ons (--skip-addons flag)"
    touch "$ADDONS_DEST/.gitkeep"
fi

echo ""
echo "Building Docker image..."
echo ""

docker build $NO_CACHE -t splunk-botsv3:latest .

# Cleanup build context
rm -rf "$ADDONS_DEST"

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
