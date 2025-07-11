#!/usr/bin/env python3
"""
Microservices Learning Application
This app demonstrates connecting to various microservices in Docker containers
Author: Learning Microservices Architecture
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

# Core libraries for different service types
import requests
import psycopg2
from pymongo import MongoClient
import redis
import pika  # RabbitMQ client
from elasticsearch import Elasticsearch
import aiohttp

# import microservice modules
import minio_service.app as minioService

# import microservices clients
from MinIOServiceClient import MinIOServiceClient

# Configure logging to track all service interactions
# Adding a time stamp on the name
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # e.g., "20250711_165900"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MicroservicesOrchestrator:
    """
    Main orchestrator that connects to and manages multiple microservices
    This simulates a real-world application that depends on various services
    """
    
    def __init__(self):
        # Service connection configurations
        # In production, these would come from environment variables or config files
        self.services_config = {
            'postgres': {
                'host': 'localhost',
                'port': 5432,
                'database': 'microservices_db',
                'user': 'postgres',
                'password': 'password'
            },
            'mongodb': {
                'host': 'localhost',
                'port': 27017,
                'database': 'microservices_mongo'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'rabbitmq': {
                'host': 'localhost',
                'port': 5672,
                'user': 'guest',
                'password': 'guest'
            },
            'elasticsearch': {
                'host': 'localhost',
                'port': 9200
            },
            'api_service': {
                'host': 'localhost',
                'port': 8080
            }
        }
        
        # Initialize connection objects
        self.postgres_conn = None
        self.mongo_client = None
        self.redis_client = None
        self.rabbitmq_connection = None
        self.elasticsearch_client = None

        # microservices clients
        self.minioClient = MinIOServiceClient()
        
    async def initialize_connections(self):
        """
        Initialize connections to all microservices
        This demonstrates service discovery and connection pooling concepts
        """
        logger.info("Initializing connections to microservices...")
        
        # Connect to PostgreSQL (Relational Database Service)
        try:
            self.postgres_conn = psycopg2.connect(
                host=self.services_config['postgres']['host'],
                port=self.services_config['postgres']['port'],
                database=self.services_config['postgres']['database'],
                user=self.services_config['postgres']['user'],
                password=self.services_config['postgres']['password']
            )
            logger.info("✓ Connected to PostgreSQL microservice")
        except Exception as e:
            logger.error(f"✗ Failed to connect to PostgreSQL: {e}")
            
        # Connect to MongoDB (NoSQL Document Database Service)
        try:
            self.mongo_client = MongoClient(
                self.services_config['mongodb']['host'],
                self.services_config['mongodb']['port']
            )
            # Test connection
            self.mongo_client.admin.command('ping')
            logger.info("✓ Connected to MongoDB microservice")
        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {e}")
            
        # Connect to Redis (In-Memory Cache Service)
        try:
            self.redis_client = redis.Redis(
                host=self.services_config['redis']['host'],
                port=self.services_config['redis']['port'],
                db=self.services_config['redis']['db'],
                decode_responses=True  # Automatically decode bytes to strings
            )
            # Test connection
            self.redis_client.ping()
            logger.info("✓ Connected to Redis microservice")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            
        # Connect to RabbitMQ (Message Queue Service)
        try:
            credentials = pika.PlainCredentials(
                self.services_config['rabbitmq']['user'],
                self.services_config['rabbitmq']['password']
            )
            parameters = pika.ConnectionParameters(
                host=self.services_config['rabbitmq']['host'],
                port=self.services_config['rabbitmq']['port'],
                credentials=credentials
            )
            self.rabbitmq_connection = pika.BlockingConnection(parameters)
            logger.info("✓ Connected to RabbitMQ microservice")
        except Exception as e:
            logger.error(f"✗ Failed to connect to RabbitMQ: {e}")
            
        # Connect to Elasticsearch (Search Engine Service)
        try:
            self.elasticsearch_client = Elasticsearch([
                f"http://{self.services_config['elasticsearch']['host']}:{self.services_config['elasticsearch']['port']}"
            ])
            # Test connection
            if self.elasticsearch_client.ping():
                logger.info("✓ Connected to Elasticsearch microservice")
            else:
                logger.error("✗ Elasticsearch ping failed")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Elasticsearch: {e}")

    async def user_service_operations(self, user_data: Dict):
        """
        Simulate user service operations across multiple microservices
        This demonstrates how a single business operation might span multiple services
        """
        logger.info(f"Processing user operation for: {user_data['name']}")
        
        # 1. Store user in PostgreSQL (Master data)
        if self.postgres_conn:
            try:
                cursor = self.postgres_conn.cursor()
                # Create table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100),
                        email VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert user data
                cursor.execute(
                    "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
                    (user_data['name'], user_data['email'])
                )
                user_id = cursor.fetchone()[0]
                self.postgres_conn.commit()
                logger.info(f"✓ User stored in PostgreSQL with ID: {user_id}")
                user_data['user_id'] = user_id
                
            except Exception as e:
                logger.error(f"✗ PostgreSQL operation failed: {e}")
                
        # 2. Store user preferences in MongoDB (Flexible schema data)
        if self.mongo_client:
            try:
                db = self.mongo_client[self.services_config['mongodb']['database']]
                collection = db.user_preferences
                
                preference_doc = {
                    'user_id': user_data.get('user_id'),
                    'preferences': user_data.get('preferences', {}),
                    'metadata': {
                        'created_at': datetime.now(),
                        'source': 'microservices_app'
                    }
                }
                
                result = collection.insert_one(preference_doc)
                logger.info(f"✓ User preferences stored in MongoDB: {result.inserted_id}")
                
            except Exception as e:
                logger.error(f"✗ MongoDB operation failed: {e}")
                
        # 3. Cache user session in Redis (Fast access data)
        if self.redis_client:
            try:
                session_key = f"user_session:{user_data.get('user_id')}"
                session_data = {
                    'user_id': user_data.get('user_id'),
                    'name': user_data['name'],
                    'login_time': datetime.now().isoformat(),
                    'status': 'active'
                }
                
                # Store with 1 hour expiration
                self.redis_client.setex(
                    session_key, 
                    3600,  # 1 hour in seconds
                    json.dumps(session_data)
                )
                logger.info(f"✓ User session cached in Redis: {session_key}")
                
            except Exception as e:
                logger.error(f"✗ Redis operation failed: {e}")
                
        # 4. Index user for search in Elasticsearch
        if self.elasticsearch_client:
            try:
                doc = {
                    'user_id': user_data.get('user_id'),
                    'name': user_data['name'],
                    'email': user_data['email'],
                    'indexed_at': datetime.now(),
                    'searchable_text': f"{user_data['name']} {user_data['email']}"
                }
                
                response = self.elasticsearch_client.index(
                    index='users',
                    id=user_data.get('user_id'),
                    body=doc
                )
                logger.info(f"✓ User indexed in Elasticsearch: {response['result']}")
                
            except Exception as e:
                logger.error(f"✗ Elasticsearch operation failed: {e}")
                
        # 5. Send welcome message via RabbitMQ (Async messaging)
        if self.rabbitmq_connection:
            try:
                channel = self.rabbitmq_connection.channel()
                
                # Declare a queue for welcome messages
                channel.queue_declare(queue='welcome_messages', durable=True)
                
                welcome_message = {
                    'user_id': user_data.get('user_id'),
                    'name': user_data['name'],
                    'email': user_data['email'],
                    'message_type': 'welcome',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Publish message to queue
                channel.basic_publish(
                    exchange='',
                    routing_key='welcome_messages',
                    body=json.dumps(welcome_message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Make message persistent / delivery_mode=1 (Non-persistent/Transient)
                    )
                )
                logger.info("✓ Welcome message sent to RabbitMQ queue")
                
            except Exception as e:
                logger.error(f"✗ RabbitMQ operation failed: {e}")

    async def call_external_api_service(self, endpoint: str = "/health"):
        """
        Make HTTP calls to external API microservices
        This demonstrates service-to-service communication
        """
        base_url = f"http://{self.services_config['api_service']['host']}:{self.services_config['api_service']['port']}"
        
        try:
            # Using async HTTP client for better performance
            # aiohttp is async and non-blocking
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}{endpoint}") as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        # Checking the content type as we were getting an
                        # 'Attempt to decode JSON with unexpected mimetype: application/octet-stream'
                        if 'application/json' in content_type:
                            data = await response.json()
                        else:
                            data = await response.text()
                        logger.info(f"✓ API service call successful: {data}")
                        return data
                    else:
                        logger.error(f"✗ API service returned status: {response.status}")
                        
        except Exception as e:
            logger.error(f"✗ API service call failed: {e}")
            # Fallback to requests library if aiohttp fails
            try:
                # requests is sync and blocking
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    logger.info(f"✓ API service call successful (fallback): {response.json()}")
                    return response.json()
            except Exception as fallback_error:
                logger.error(f"✗ Fallback API call also failed: {fallback_error}")
                
        return None

    async def search_users(self, query: str) -> List[Dict]:
        """
        Search for users using Elasticsearch
        Demonstrates search microservice capabilities
        """
        if not self.elasticsearch_client:
            logger.error("Elasticsearch not connected")
            return []
            
        try:
            # Perform search query
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name", "email", "searchable_text"]
                    }
                }
            }
            
            response = self.elasticsearch_client.search(
                index='users',
                body=search_body
            )
            
            # Extract results
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    'user_id': hit['_id'],
                    'score': hit['_score'],
                    'data': hit['_source']
                })
                
            logger.info(f"✓ Search completed: {len(results)} results found")
            return results
            
        except Exception as e:
            logger.error(f"✗ Search operation failed: {e}")
            return []

    async def get_cached_user_session(self, user_id: int) -> Optional[Dict]:
        """
        Retrieve user session from Redis cache
        Demonstrates caching microservice pattern
        """
        if not self.redis_client:
            logger.error("Redis not connected")
            return None
            
        try:
            session_key = f"user_session:{user_id}"
            session_data = self.redis_client.get(session_key)
            
            if session_data:
                parsed_data = json.loads(session_data)
                logger.info(f"✓ Retrieved session from cache for user {user_id}")
                return parsed_data
            else:
                logger.info(f"No cached session found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"✗ Cache retrieval failed: {e}")
            return None

    async def process_message_queue(self):
        """
        Process messages from RabbitMQ queue
        Demonstrates asynchronous message processing
        """
        if not self.rabbitmq_connection:
            logger.error("RabbitMQ not connected")
            return
            
        try:
            channel = self.rabbitmq_connection.channel()
            
            # Declare the queue (in case it doesn't exist)
            channel.queue_declare(queue='welcome_messages', durable=True)
            
            def callback(ch, method, properties, body):
                """Process each message from the queue"""
                try:
                    message = json.loads(body)
                    logger.info(f"Processing message: {message['message_type']} for user {message['user_id']}")
                    
                    # Simulate message processing
                    time.sleep(1)
                    
                    # Acknowledge message processing
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info("✓ Message processed successfully")
                    
                except Exception as e:
                    logger.error(f"✗ Message processing failed: {e}")
                    # Reject message and requeue. IMPORTANT to requeue if fails
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            # Set up consumer
            channel.basic_qos(prefetch_count=1)  # Process one message at a time
            channel.basic_consume(queue='welcome_messages', on_message_callback=callback)
            
            logger.info("Started consuming messages from RabbitMQ...")
            # Process a few messages then stop (for demo purposes)
            for i in range(3):
                channel.connection.process_data_events(time_limit=2)
                
        except Exception as e:
            logger.error(f"✗ Message queue processing failed: {e}")

    async def health_check_all_services(self) -> Dict[str, bool]:
        """
        Perform health checks on all microservices
        This is crucial for monitoring and alerting in production
        """
        logger.info("Performing health checks on all microservices...")
        health_status = {}
        
        # Check PostgreSQL
        try:
            if self.postgres_conn:
                cursor = self.postgres_conn.cursor()
                cursor.execute("SELECT 1")
                health_status['postgres'] = True
                logger.info("✓ PostgreSQL health check passed")
            else:
                health_status['postgres'] = False
        except Exception as e:
            health_status['postgres'] = False
            logger.error(f"✗ PostgreSQL health check failed: {e}")
            
        # Check MongoDB
        try:
            if self.mongo_client:
                self.mongo_client.admin.command('ping')
                health_status['mongodb'] = True
                logger.info("✓ MongoDB health check passed")
            else:
                health_status['mongodb'] = False
        except Exception as e:
            health_status['mongodb'] = False
            logger.error(f"✗ MongoDB health check failed: {e}")
            
        # Check Redis
        try:
            if self.redis_client:
                self.redis_client.ping()
                health_status['redis'] = True
                logger.info("✓ Redis health check passed")
            else:
                health_status['redis'] = False
        except Exception as e:
            health_status['redis'] = False
            logger.error(f"✗ Redis health check failed: {e}")
            
        # Check RabbitMQ
        try:
            if self.rabbitmq_connection and self.rabbitmq_connection.is_open:
                health_status['rabbitmq'] = True
                logger.info("✓ RabbitMQ health check passed")
            else:
                health_status['rabbitmq'] = False
        except Exception as e:
            health_status['rabbitmq'] = False
            logger.error(f"✗ RabbitMQ health check failed: {e}")
            
        # Check Elasticsearch
        try:
            if self.elasticsearch_client and self.elasticsearch_client.ping():
                health_status['elasticsearch'] = True
                logger.info("✓ Elasticsearch health check passed")
            else:
                health_status['elasticsearch'] = False
        except Exception as e:
            health_status['elasticsearch'] = False
            logger.error(f"✗ Elasticsearch health check failed: {e}")
            
        # Check external API service
        api_health = await self.call_external_api_service("/health")
        health_status['api_service'] = api_health is not None
        
        return health_status

    async def cleanup_connections(self):
        """
        Clean up all connections when shutting down
        Important for resource management
        """
        logger.info("Cleaning up microservice connections...")
        
        if self.postgres_conn:
            self.postgres_conn.close()
            logger.info("✓ PostgreSQL connection closed")
            
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("✓ MongoDB connection closed")
            
        if self.redis_client:
            self.redis_client.close()
            logger.info("✓ Redis connection closed")
            
        if self.rabbitmq_connection:
            self.rabbitmq_connection.close()
            logger.info("✓ RabbitMQ connection closed")
    
    def createLastRunLogFile():
        last_run_file_name = "last_run.txt"
        with open(last_run_file_name, "w") as file:
            file.write(f"{timestamp}")
        
        logger.debug("✓ Last run file created successfully")



async def main():
    """
    Main application entry point
    Demonstrates a complete microservices workflow
    """
    logger.info(f"{timestamp}. === Microservices Learning Application Started ===")
    
    # Initialize the orchestrator
    orchestrator = MicroservicesOrchestrator()
    
    try:
        # Step 1: Initialize all microservice connections
        await orchestrator.initialize_connections()
        
        # Step 2: Perform health checks
        health_status = await orchestrator.health_check_all_services()
        logger.info(f"{timestamp}. Health Status: {health_status}")
        
        # Step 3: Simulate user operations across multiple services
        sample_users = [
            {
                'name': 'Alice Johnson',
                'email': 'alice@example.com',
                'preferences': {
                    'theme': 'dark',
                    'notifications': True,
                    'language': 'en'
                }
            },
            {
                'name': 'Bob Smith',
                'email': 'bob@example.com',
                'preferences': {
                    'theme': 'light',
                    'notifications': False,
                    'language': 'es'
                }
            }
        ]
        
        # Process each user through all microservices
        for user in sample_users:
            await orchestrator.user_service_operations(user)
            await asyncio.sleep(1)  # Brief pause between operations
            
        # Step 4: Demonstrate search capabilities
        search_results = await orchestrator.search_users("Alice")
        logger.info(f"{timestamp}. Search results: {len(search_results)} found")
        
        # Step 5: Demonstrate caching, pulling the data from Redis
        cached_session = await orchestrator.get_cached_user_session(1)
        if cached_session:
            logger.info(f"{timestamp}. Cached session found: {cached_session['name']}")
            
        # Step 6: Process message queue
        await orchestrator.process_message_queue()
        
        # Step 7: Make external API calls
        await orchestrator.call_external_api_service("/status")
        
        # calling the MinIO service through the client
        await orchestrator.minioClient.upload_last_run_file('requirements.txt', f"{timestamp}.txt")

        logger.info(f"{timestamp}. === All microservices operations completed successfully ===")
        
    except KeyboardInterrupt:
        logger.info(f"{timestamp}. Application interrupted by user")
    except Exception as e:
        logger.error(f"{timestamp}. Application error: {e}")
    finally:
        # Always clean up connections
        await orchestrator.cleanup_connections()
        logger.info(f"{timestamp}. === Microservices Learning Application Finished ===")


# In a Python file, the code within the if __name__ == "__main__": block is executed when the file is run directly as a script. 
# This block is not a function in itself, but rather a conditional statement that determines whether the current file is being executed 
# as the main program or being imported as a module into another program.
if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
