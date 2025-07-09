# Python microservices application

This application demonstrates how to connect to multiple microservices running in Docker containers.

## Architecture Overview

The application connects to these microservices:

1. **PostgreSQL** - Relational database for structured data
2. **MongoDB** - NoSQL document database for flexible schemas
3. **Redis** - In-memory cache for fast data access
4. **RabbitMQ** - Message queue for asynchronous communication
5. **Elasticsearch** - Search engine for full-text search capabilities
6. **API Service** - REST API microservice (simulated with nginx)

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ installed
- Git (to clone or download the code)

## Setup Instructions

# I had to first install Docker
#
# When you use brew install docker without --cask, it only installs the Docker client (CLI tools), 
# not the Docker daemon (the service that runs containers).
# ALWAYS install using --cask command
#
brew install --cask docker

# Then I had to install docker-compose
brew install docker-compose

# Setup the installation of required dependencies
chmod +x startup.sh && ./startup.sh

#The following came with an error so I had to run:
# pip install -r requirements.txt
# Also, I did create the API response files mentioned in the following steps .. before running the microservices app
python3 microservices_app.py

# Test the Postgres DB data using:
psql -h localhost -p 5432 -U postgres -d microservices_db
# Test the Mongo DB data using:
mongosh --host localhost --port 27017 microservices_mongo
# Test the Redis data using:
redis-cli -h localhost -p 6379 -n 0
> KEYS *
> GET user_session:6
# Test the data in the RabbitMQ
http://localhost:15672/#/
guest / guest
# Check the API service
curl -X GET http://localhost:8080/status

### 1. Start All Microservices

First, create the API response files directory:

```bash
mkdir -p api_responses
```

Create mock API responses:

```bash
# Create health endpoint response
echo '{"status": "healthy", "service": "api_service", "timestamp": "2024-01-01T00:00:00Z"}' > api_responses/health

# Create status endpoint response
echo '{"status": "running", "version": "1.0.0", "uptime": "24h"}' > api_responses/status
```

Start all services using Docker Compose:

```bash
docker-compose up -d
```

### 2. Verify Services Are Running

Check that all containers are healthy:

```bash
docker-compose ps
```

You should see all services with "healthy" status.

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python microservices_app.py
```

## Service Access Points

Once running, you can access:

- **PostgreSQL**: `localhost:5432` (user: postgres, password: password)
- **MongoDB**: `localhost:27017`
- **Redis**: `localhost:6379`
- **RabbitMQ**: `localhost:5672` (Management UI: http://localhost:15672)
- **Elasticsearch**: `localhost:9200`
- **API Service**: `localhost:8080`
- **Adminer** (DB GUI): `localhost:8081`

## What the Application Does

1. **Connection Management**: Establishes connections to all microservices
2. **Health Checks**: Monitors the health of all services
3. **User Operations**: Demonstrates how a single business operation spans multiple services:
   - Stores user data in PostgreSQL
   - Saves user preferences in MongoDB
   - Caches session data in Redis
   - Indexes user for search in Elasticsearch
   - Sends welcome messages via RabbitMQ
4. **Search Operations**: Performs full-text search using Elasticsearch
5. **Caching**: Demonstrates fast data retrieval from Redis
6. **Message Processing**: Shows asynchronous message handling with RabbitMQ
7. **API Calls**: Makes HTTP requests to external services

## Key Microservices Concepts Demonstrated

### Service Discovery
- Each service is configured with connection details
- Health checks ensure services are available
- Graceful handling of service failures

### Data Consistency
- Shows how data flows between different services
- Demonstrates eventual consistency patterns
- Handles failures gracefully with rollback strategies

### Communication Patterns
- **Synchronous**: Direct HTTP calls between services
- **Asynchronous**: Message queues for decoupled communication
- **Caching**: Redis for fast data access and reduced database load

### Scalability Patterns
- Connection pooling for efficient resource usage
- Async operations for better performance
- Caching strategies to reduce backend load

### Monitoring and Observability
- Health checks for all services
- Comprehensive logging for debugging
- Error handling and recovery mechanisms

## Kubernetes Preparation

This setup prepares you for Kubernetes by demonstrating:

1. **Service Isolation**: Each service runs in its own container
2. **Configuration Management**: Environment variables and config files
3. **Networking**: Inter-service communication patterns
4. **Resource Management**: CPU and memory considerations
5. **Scaling**: Understanding how services can be scaled independently

## Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check Docker logs
docker-compose logs [service_name]

# Restart specific service
docker-compose restart [service_name]
```

**Connection errors:**
```bash
# Check if ports are available
netstat -an | grep [port_number]

# Verify service health
docker-compose exec [service_name] [health_check_command]
```

**Python import errors:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Port Conflicts

If you have port conflicts, modify the docker-compose.yml file:

```yaml
ports:
  - "5433:5432"  # Change host port (left side)
```

Then update the Python app configuration accordingly.

## Advanced Exercises

Once you understand the basic setup, try these exercises:

1. **Add a new microservice** (e.g., MinIO for object storage)
2. **Implement circuit breaker pattern** for fault tolerance
3. **Add authentication service** with JWT tokens
4. **Create a load balancer** to distribute requests
5. **Implement distributed tracing** with Jaeger
6. **Add monitoring** with Prometheus and Grafana

## Kubernetes Migration

To move this to Kubernetes:

1. **Convert to Kubernetes manifests**:
   - Deployments for each service
   - Services for networking
   - ConfigMaps for configuration
   - Secrets for sensitive data

2. **Consider using Helm charts** for easier management

3. **Implement Kubernetes-specific features**:
   - Horizontal Pod Autoscaler
   - Ingress controllers
   - Persistent volumes
   - Service mesh (Istio)

## Production Considerations

When moving to production:

1. **Security**: Use proper authentication and authorization
2. **Monitoring**: Implement comprehensive logging and metrics
3. **Backup**: Regular backups of persistent data
4. **Scaling**: Auto-scaling based on demand
5. **CI/CD**: Automated testing and deployment
6. **Resource Limits**: Set appropriate CPU/memory limits

## Learning Resources

- **Docker**: https://docs.docker.com/
- **Kubernetes**: https://kubernetes.io/docs/
- **Microservices Patterns**: https://microservices.io/
- **12-Factor App**: https://12factor.net/

## Next Steps

1. Run the application and observe the logs
2. Try stopping individual services and see how the app handles failures
3. Modify the code to add new operations
4. Experiment with different data flows
5. Practice converting the Docker Compose setup to Kubernetes manifests
