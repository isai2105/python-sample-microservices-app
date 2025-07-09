#!/bin/bash

# Quick Start Script for Microservices Learning Application
# This script sets up everything you need to run the application

echo "🚀 Starting Microservices Learning Environment Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

print_status "All prerequisites are installed!"

# Create API responses directory
print_status "Creating API responses directory..."
mkdir -p api_responses

# Create mock API responses
print_status "Creating mock API responses..."
echo '{"status": "healthy", "service": "api_service", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > api_responses/health
echo '{"status": "running", "version": "1.0.0", "uptime": "0h", "requests_handled": 0}' > api_responses/status
echo '{"message": "Welcome to the Microservices API!", "endpoints": ["/health", "/status"]}' > api_responses/index.html

# Check if services are already running
print_status "Checking for existing services..."
if docker-compose ps | grep -q "Up"; then
    print_warning "Some services are already running. Stopping them first..."
    docker-compose down
fi

# Start all services
print_status "Starting all microservices..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_status "Checking service health..."
services=("postgres" "mongodb" "redis" "rabbitmq" "elasticsearch" "api_service")
all_healthy=true

for service in "${services[@]}"; do
    if docker-compose ps | grep "$service" | grep -q "healthy\|Up"; then
        print_status "✓ $service is running"
    else
        print_warning "✗ $service may not be ready yet"
        all_healthy=false
    fi
done

if [ "$all_healthy" = false ]; then
    print_warning "Some services may still be starting up. This is normal for the first run."
    print_warning "You can check status with: docker-compose ps"
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    print_error "pip is not installed. Please install pip first."
    exit 1
fi

# Display service URLs
print_status "🎉 Setup complete! Services are available at:"
echo ""
echo "📊 Service Endpoints:"
echo "  PostgreSQL:    localhost:5432 (user: postgres, password: password)"
echo "  MongoDB:       localhost:27017"
echo "  Redis:         localhost:6379"
echo "  RabbitMQ:      localhost:5672 (Management UI: http://localhost:15672)"
echo "  Elasticsearch: http://localhost:9200"
echo "  API Service:   http://localhost:8080"
echo "  Adminer (DB):  http://localhost:8081"
echo ""
echo "🚀 To run the application:"
echo "  python3 microservices_app.py"
echo ""
echo "📋 Useful commands:"
echo "  docker-compose ps              # Check service status"
echo "  docker-compose logs [service]  # View service logs"
echo "  docker-compose down            # Stop all services"
echo "  docker-compose restart         # Restart all services"
echo ""
echo "Happy learning! 🎓"