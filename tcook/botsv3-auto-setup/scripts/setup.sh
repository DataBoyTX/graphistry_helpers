#!/bin/bash
# Complete setup script for Splunk BOTSv3 Docker environment
# This script builds the Docker image, starts the container, and sets up the Python client

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${CYAN}"
    echo "============================================"
    echo "$1"
    echo "============================================"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker installed: $DOCKER_VERSION"
    else
        print_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose installed: $COMPOSE_VERSION"
    elif docker compose version &> /dev/null; then
        print_success "Docker Compose (plugin) available"
    else
        print_warning "Docker Compose not found - using docker run"
    fi
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python installed: $PYTHON_VERSION"
    else
        print_warning "Python 3 not found - Python client setup will be skipped"
    fi
    
    echo ""
}

build_docker_image() {
    print_header "Building Docker Image"

    # Dockerfile is in scripts directory
    cd "$SCRIPT_DIR"
    
    echo "This will download:"
    echo "  - Splunk Enterprise 9.1.0.2 (~500MB)"
    echo "  - BOTSv3 Dataset (~320MB)"
    echo ""
    echo "Total download size: ~820MB"
    echo "Build time: 5-15 minutes depending on network speed"
    echo ""
    
    read -p "Continue? [y/N] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Build cancelled"
        exit 0
    fi
    
    echo ""
    docker build -t splunk-botsv3:latest .
    
    print_success "Docker image built successfully"
    echo ""
}

start_container() {
    print_header "Starting Splunk Container"

    # docker-compose.yml is in scripts directory
    cd "$SCRIPT_DIR"
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q '^splunk-botsv3$'; then
        print_warning "Container 'splunk-botsv3' already exists"
        read -p "Remove and recreate? [y/N] " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker rm -f splunk-botsv3 2>/dev/null || true
        else
            if docker ps --format '{{.Names}}' | grep -q '^splunk-botsv3$'; then
                print_success "Container already running"
                return
            else
                docker start splunk-botsv3
                print_success "Existing container started"
                return
            fi
        fi
    fi
    
    # Start with docker-compose if available
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    elif docker compose version &> /dev/null 2>&1; then
        docker compose up -d
    else
        docker run -d \
            --name splunk-botsv3 \
            -p 8000:8000 \
            -p 8089:8089 \
            -p 9997:9997 \
            -p 8088:8088 \
            -e SPLUNK_START_ARGS='--accept-license' \
            -e SPLUNK_PASSWORD='changeme123' \
            splunk-botsv3:latest
    fi
    
    print_success "Container started"
    echo ""
}

wait_for_splunk() {
    print_header "Waiting for Splunk to Initialize"
    
    echo "Splunk is starting up..."
    echo "This typically takes 2-3 minutes for first run."
    echo ""
    
    MAX_ATTEMPTS=60
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/en-US/account/login 2>/dev/null | grep -q "200"; then
            print_success "Splunk is ready!"
            echo ""
            return 0
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
        printf "\r  Waiting... [%d/%d]" $ATTEMPT $MAX_ATTEMPTS
        sleep 5
    done
    
    echo ""
    print_error "Timeout waiting for Splunk to start"
    print_warning "Check container logs: docker logs splunk-botsv3"
    return 1
}

setup_python_client() {
    print_header "Setting Up Python Client"

    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 not found - skipping Python client setup"
        return
    fi

    # python_client is under scripts directory
    cd "$SCRIPT_DIR/python_client"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    
    echo "Installing dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    
    print_success "Python dependencies installed"
    
    # Create .env file
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Environment file created (.env)"
    fi
    
    echo ""
}

test_connection() {
    print_header "Testing Splunk Connection"

    cd "$SCRIPT_DIR/python_client"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        
        echo "Running health check..."
        python splunk_client.py health
        
        echo ""
        echo "Testing BOTSv3 search..."
        python splunk_client.py search "index=botsv3 earliest=0 | head 5" -c 5
    else
        # Test with curl
        echo "Testing REST API with curl..."
        
        if curl -sk -u admin:changeme123 https://localhost:8089/services/server/info | grep -q "serverName"; then
            print_success "REST API is accessible"
        else
            print_error "REST API test failed"
        fi
    fi
    
    echo ""
}

print_summary() {
    print_header "Setup Complete!"
    
    echo -e "${GREEN}Splunk BOTSv3 is ready to use!${NC}"
    echo ""
    echo "Access Points:"
    echo "  Web UI:    http://localhost:8000"
    echo "  REST API:  https://localhost:8089"
    echo ""
    echo "Credentials:"
    echo "  Username:  admin"
    echo "  Password:  changeme123"
    echo ""
    echo "BOTSv3 Search:"
    echo "  index=botsv3 earliest=0"
    echo ""
    echo "Python Client Usage:"
    echo "  cd python_client"
    echo "  source venv/bin/activate"
    echo "  python splunk_client.py --help"
    echo "  python splunk_client.py search 'index=botsv3 | head 10'"
    echo "  python splunk_client.py interactive"
    echo ""
    echo "Docker Commands:"
    echo "  Stop:    docker-compose down"
    echo "  Start:   docker-compose up -d"
    echo "  Logs:    docker logs -f splunk-botsv3"
    echo "  Shell:   docker exec -it splunk-botsv3 bash"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║     Splunk BOTSv3 Docker Setup                        ║"
    echo "║     Boss of the SOC v3 Challenge Environment          ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""
    
    check_prerequisites
    build_docker_image
    start_container
    wait_for_splunk
    setup_python_client
    test_connection
    print_summary
}

# Handle command line arguments
case "${1:-}" in
    --build-only)
        check_prerequisites
        build_docker_image
        ;;
    --start-only)
        start_container
        wait_for_splunk
        ;;
    --python-only)
        setup_python_client
        ;;
    --test)
        test_connection
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  --build-only   Only build the Docker image"
        echo "  --start-only   Only start the container"
        echo "  --python-only  Only setup Python client"
        echo "  --test         Only run connection tests"
        echo "  --help         Show this help message"
        echo ""
        echo "With no options, runs complete setup."
        ;;
    *)
        main
        ;;
esac
