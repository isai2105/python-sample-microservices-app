from flask import Flask, request, jsonify, send_file
from minio import Minio
from minio.error import S3Error
import os
from datetime import timedelta
import io
import logging
from functools import wraps
import traceback

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MinIO configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'False').lower() == 'true'
DEFAULT_BUCKET = os.getenv('DEFAULT_BUCKET', 'default-bucket')

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

def handle_errors(f):
    """Decorator to handle MinIO errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except S3Error as e:
            logger.error(f"MinIO S3 Error: {e}")
            return jsonify({'error': f'MinIO error: {e}'}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test MinIO connection
        minio_client.list_buckets()
        return jsonify({'status': 'healthy', 'service': 'minio-microservice'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

@app.route('/buckets', methods=['GET'])
@handle_errors
def list_buckets():
    """List all buckets"""
    buckets = minio_client.list_buckets()
    bucket_list = [{'name': bucket.name, 'creation_date': bucket.creation_date.isoformat()} 
                   for bucket in buckets]
    return jsonify({'buckets': bucket_list}), 200

@app.route('/buckets/<bucket_name>', methods=['POST'])
@handle_errors
def create_bucket(bucket_name):
    """Create a new bucket"""
    if minio_client.bucket_exists(bucket_name):
        return jsonify({'message': f'Bucket {bucket_name} already exists'}), 409
    
    minio_client.make_bucket(bucket_name)
    logger.info(f"Created bucket: {bucket_name}")
    return jsonify({'message': f'Bucket {bucket_name} created successfully'}), 201

@app.route('/buckets/<bucket_name>', methods=['DELETE'])
@handle_errors
def delete_bucket(bucket_name):
    """Delete a bucket"""
    if not minio_client.bucket_exists(bucket_name):
        return jsonify({'error': f'Bucket {bucket_name} does not exist'}), 404
    
    # Check if bucket is empty
    objects = list(minio_client.list_objects(bucket_name))
    if objects:
        return jsonify({'error': f'Bucket {bucket_name} is not empty'}), 400
    
    minio_client.remove_bucket(bucket_name)
    logger.info(f"Deleted bucket: {bucket_name}")
    return jsonify({'message': f'Bucket {bucket_name} deleted successfully'}), 200

@app.route('/buckets/<bucket_name>/objects', methods=['GET'])
@handle_errors
def list_objects(bucket_name):
    """List objects in a bucket"""
    if not minio_client.bucket_exists(bucket_name):
        return jsonify({'error': f'Bucket {bucket_name} does not exist'}), 404
    
    prefix = request.args.get('prefix', '')
    recursive = request.args.get('recursive', 'false').lower() == 'true'
    
    objects = minio_client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
    object_list = []
    
    for obj in objects:
        object_list.append({
            'name': obj.object_name,
            'size': obj.size,
            'etag': obj.etag,
            'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
            'content_type': obj.content_type
        })
    
    return jsonify({'objects': object_list}), 200

@app.route('/buckets/<bucket_name>/objects/<path:object_name>', methods=['POST'])
@handle_errors
def upload_object(bucket_name, object_name):
    """Upload an object to a bucket"""
    if not minio_client.bucket_exists(bucket_name):
        return jsonify({'error': f'Bucket {bucket_name} does not exist'}), 404
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get file data
    file_data = file.read()
    file_size = len(file_data)
    
    # Upload to MinIO
    minio_client.put_object(
        bucket_name,
        object_name,
        io.BytesIO(file_data),
        file_size,
        content_type=file.content_type or 'application/octet-stream'
    )
    
    logger.info(f"Uploaded object: {object_name} to bucket: {bucket_name}")
    return jsonify({
        'message': f'Object {object_name} uploaded successfully',
        'size': file_size,
        'content_type': file.content_type
    }), 201

@app.route('/buckets/<bucket_name>/objects/<path:object_name>', methods=['GET'])
@handle_errors
def download_object(bucket_name, object_name):
    """Download an object from a bucket"""
    if not minio_client.bucket_exists(bucket_name):
        return jsonify({'error': f'Bucket {bucket_name} does not exist'}), 404
    
    try:
        # Get object
        response = minio_client.get_object(bucket_name, object_name)
        
        # Create a BytesIO object from the response data
        file_data = io.BytesIO(response.read())
        response.close()
        
        # Get object info for content type
        stat = minio_client.stat_object(bucket_name, object_name)
        
        return send_file(
            file_data,
            as_attachment=True,
            download_name=object_name.split('/')[-1],
            mimetype=stat.content_type or 'application/octet-stream'
        )
        
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return jsonify({'error': f'Object {object_name} not found'}), 404
        raise

@app.route('/buckets/<bucket_name>/objects/<path:object_name>', methods=['DELETE'])
@handle_errors
def delete_object(bucket_name, object_name):
    """Delete an object from a bucket"""
    if not minio_client.bucket_exists(bucket_name):
        return jsonify({'error': f'Bucket {bucket_name} does not exist'}), 404
    
    try:
        minio_client.remove_object(bucket_name, object_name)
        logger.info(f"Deleted object: {object_name} from bucket: {bucket_name}")
        return jsonify({'message': f'Object {object_name} deleted successfully'}), 200
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return jsonify({'error': f'Object {object_name} not found'}), 404
        raise

@app.route('/buckets/<bucket_name>/objects/<path:object_name>/url', methods=['GET'])
@handle_errors
def get_presigned_url(bucket_name, object_name):
    """Generate a presigned URL for an object"""
    if not minio_client.bucket_exists(bucket_name):
        return jsonify({'error': f'Bucket {bucket_name} does not exist'}), 404
    
    # Get expiration time (default 1 hour)
    expires = int(request.args.get('expires', 3600))
    
    try:
        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(seconds=expires)
        )
        
        return jsonify({
            'url': url,
            'expires_in': expires,
            'object_name': object_name
        }), 200
        
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return jsonify({'error': f'Object {object_name} not found'}), 404
        raise

@app.route('/buckets/<bucket_name>/objects/<path:object_name>/info', methods=['GET'])
@handle_errors
def get_object_info(bucket_name, object_name):
    """Get object information"""
    if not minio_client.bucket_exists(bucket_name):
        return jsonify({'error': f'Bucket {bucket_name} does not exist'}), 404
    
    try:
        stat = minio_client.stat_object(bucket_name, object_name)
        
        return jsonify({
            'object_name': object_name,
            'size': stat.size,
            'etag': stat.etag,
            'last_modified': stat.last_modified.isoformat(),
            'content_type': stat.content_type,
            'metadata': stat.metadata
        }), 200
        
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return jsonify({'error': f'Object {object_name} not found'}), 404
        raise

@app.cli.command("init")
def initialize():
    """Initialize default bucket if it doesn't exist"""
    try:
        if not minio_client.bucket_exists(DEFAULT_BUCKET):
            minio_client.make_bucket(DEFAULT_BUCKET)
            logger.info(f"Created default bucket: {DEFAULT_BUCKET}")
    except Exception as e:
        logger.error(f"Failed to initialize default bucket: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010, debug=os.getenv('DEBUG', 'False').lower() == 'true')
