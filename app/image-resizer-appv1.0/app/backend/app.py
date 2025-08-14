from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from prometheus_client import Counter, Histogram, generate_latest
from time import time
from PIL import Image
import io
import logging
from pythonjsonlogger.json import JsonFormatter
import socket
import uuid
import datetime
import requests
import json
import random
import string
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from models import db, bcrypt, User, Request
from confluent_kafka import Producer
from flasgger import Swagger
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-please-change')
# Use FRONTEND_ALLOWED env variable, default to http://localhost:3000
cors_origin = os.environ.get('FRONTEND_ALLOWED', '34.244.54.114')
CORS(app, resources={r"/*": {"origins": cors_origin}}, supports_credentials=True)
Swagger(app, config={
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/docs/apispec_1.json',
            "rule_filter": lambda rule: True,  # all endpoints
            "model_filter": lambda tag: True,  # all models
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
})

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'gif', 'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ENABLE_ZIP = os.environ.get('ENABLE_ZIP', '0') == '1'
print(f"------------------------------------------------")
print(f"Zip processing feature {'ENABLED' if ENABLE_ZIP else 'DISABLED'}")
print(f"------------------------------------------------")
print()

KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_ZIP_TOPIC = os.environ.get('KAFKA_ZIP_TOPIC', 'zip-requests')

# Only create the Kafka producer if zip processing is enabled
if ENABLE_ZIP:
    from confluent_kafka import Producer
    kafka_producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
else:
    kafka_producer = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_zip(filename):
    return filename.lower().endswith('.zip')

# Metrics
REQUEST_COUNT = Counter('request_count', 'Number of requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['endpoint'])
# New metrics for performance analysis
RESIZE_PROCESSING_TIME = Histogram('image_resize_processing_seconds', 'Image resize processing time (seconds)')
RESIZE_SUCCESS_COUNT = Counter('image_resize_success_total', 'Number of successful image resizes')
RESIZE_ERROR_COUNT = Counter('image_resize_error_total', 'Number of image resize errors', ['error_type'])

@app.before_request
def before_request():
    request.start_time = time()

@app.after_request
def after_request(response):
    latency = time() - request.start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path).inc()
    REQUEST_LATENCY.labels(endpoint=request.path).observe(latency)
    return response

def make_log_entry(alert=None, code=None, message=None, endpoint=None, extra=None, correlation_id=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    log_entry = {
        'timestamp': int(now.timestamp() * 1000),
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'alert': alert,
        'component': 'Image-Resizer Flask backend',
        'node': socket.gethostname(),
        'correlationId': correlation_id or str(uuid.uuid4()),
        'code': code,
        'message': message,
        'endpoint': endpoint,
    }
    if extra:
        log_entry['extra'] = extra
    wrapper = {
        'ts': log_entry['timestamp'],
        'messages': [log_entry]
    }
    return wrapper

def send_to_fluentd(log_entry):
    try:
        requests.post('http://localhost:9880/backend.logs', json=log_entry, timeout=0.5)
    except Exception:
        pass

# Set up JSON logger for stdout only
logger = logging.getLogger("image-resizer")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

@app.route('/')
def index():
    """
    Backend status and documentation link.
    ---
    responses:
      200:
        description: Backend is running and provides a link to the API docs.
    """
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image-Resizer Flask API Backend</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>Image-Resizer app's Flask API backend is running</h1>
        <p>See the documentation at <a href="/docs">/docs</a></p>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload():
    """
    Upload an image or zip file for resizing.
    ---
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: image
        type: file
        required: true
        description: The image or zip file to upload.
      - in: formData
        name: percent
        type: integer
        required: true
        description: The percent to reduce the image(s) to (1-99).
    responses:
      200:
        description: Image resized or zip accepted
      400:
        description: Invalid input
      500:
        description: Internal server error
    """
    image = request.files.get('image')
    percent = request.form.get('percent')
    correlation_id = request.headers.get('X-Correlation-Id') or str(uuid.uuid4())
    log_context = {
        "event": "image_upload",
        "client_ip": request.remote_addr,
        "customer_filename": image.filename if image else None,
        "storage_filename": None,  # Will be set after upload_filename is generated
        "percent": percent,
        "host": socket.gethostname()
    }
    endpoint = '/upload'
    if not image:
        entry = make_log_entry(alert='action', code='NO_FILE_UPLOADED', message='No file uploaded', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
        logger.error(entry)
        send_to_fluentd(entry)
        RESIZE_ERROR_COUNT.labels(error_type='no_file_uploaded').inc()
        return jsonify({'error': 'No file uploaded'}), 400
    ext = image.filename.rsplit('.', 1)[-1].lower()
    if allowed_file(image.filename):
        try:
            percent = int(percent)
            if not (1 <= percent <= 99):
                raise ValueError
        except Exception:
            entry = make_log_entry(alert='monitor', code='INVALID_PERCENTAGE', message='Invalid percentage', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
            logger.warning(entry)
            send_to_fluentd(entry)
            RESIZE_ERROR_COUNT.labels(error_type='invalid_percent').inc()
            return jsonify({'error': 'Invalid percentage'}), 400
        try:
            # Save original with random prefix and truncate if needed
            upload_filename = safe_upload_filename(image.filename)
            log_context["storage_filename"] = upload_filename
            filepath = os.path.join(UPLOAD_FOLDER, upload_filename)
            image.save(filepath)
            orig_size = os.path.getsize(filepath)
            img = Image.open(filepath)
            new_size = (max(1, int(img.width * percent / 100)), max(1, int(img.height * percent / 100)))
            img_resized = img.resize(new_size, Image.LANCZOS)
            reduced_name = safe_reduced_filename(upload_filename)
            reduced_path = os.path.join(UPLOAD_FOLDER, reduced_name)
            import time as t
            start = t.time()
            img_resized.save(reduced_path)
            elapsed = t.time() - start
            RESIZE_PROCESSING_TIME.observe(elapsed)
            RESIZE_SUCCESS_COUNT.inc()
            extra = {
                **log_context,
                "original_size": orig_size,
                "percent": percent,
                "algorithm": "LANCZOS",
                "processing_time": elapsed,
                "output_file": reduced_name
            }
            entry = make_log_entry(alert='info', code='RESIZE_SUCCESS', message='Image resized', endpoint=endpoint, extra=extra, correlation_id=correlation_id)
            logger.info(entry)
            send_to_fluentd(entry)
            # Store request in DB if user is logged in and DB is enabled
            if USE_DATABASE and current_user.is_authenticated:
                req = Request(
                    user_id=current_user.id,
                    request_created=datetime.datetime.now(datetime.UTC),
                    correlation_id=correlation_id,
                    customer_filename=image.filename,
                    original_resolution=f"{img.width}x{img.height}",
                    original_filesize=orig_size,
                    resized_filename=reduced_name,
                    resized_resolution=f"{new_size[0]}x{new_size[1]}",
                    new_filesize=os.path.getsize(reduced_path),
                    reduce_to_percent=percent,
                    status='Success',
                    failure_reason=None,
                    expiry=None
                )
                db.session.add(req)
                db.session.commit()
            return jsonify({'message': 'Image resized', 'filename': reduced_name, 'upload_filename': upload_filename}), 200
        except Exception as e:
            entry = make_log_entry(alert='emergency', code='FATAL_ERROR', message=f'Fatal error: {str(e)}', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
            logger.critical(entry)
            send_to_fluentd(entry)
            RESIZE_ERROR_COUNT.labels(error_type='fatal_error').inc()
            # Store failed request in DB if user is logged in and DB is enabled
            if USE_DATABASE and current_user.is_authenticated:
                req = Request(
                    user_id=current_user.id,
                    request_created=datetime.datetime.now(datetime.UTC),
                    correlation_id=correlation_id,
                    customer_filename=image.filename if image else None,
                    original_resolution=None,
                    original_filesize=None,
                    resized_filename=None,
                    resized_resolution=None,
                    new_filesize=None,
                    reduce_to_percent=percent if 'percent' in locals() else None,
                    status='Failure',
                    failure_reason=str(e),
                    expiry=None
                )
                db.session.add(req)
                db.session.commit()
            return jsonify({'error': 'Internal server error'}), 500
    elif allowed_zip(image.filename):
        if not ENABLE_ZIP:
            # Log emergency and return A3 error if zip processing is not enabled
            entry = make_log_entry(alert='emergency', code='A3', message='Zip processing not enabled in backend', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
            logger.critical(entry)
            send_to_fluentd(entry)
            return jsonify({'error': 'Error A3: Unable to process zip files. Try again later'}), 400
        import zipfile, tempfile
        # Save zip to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
            image.save(tmp_zip)
            tmp_zip_path = tmp_zip.name
        try:
            # Validate zip contents robustly
            try:
                with zipfile.ZipFile(tmp_zip_path, 'r') as zf:
                    bad = [info.filename for info in zf.infolist() if not info.is_dir() and not allowed_file(info.filename)]
            except zipfile.BadZipFile:
                os.remove(tmp_zip_path)
                entry = make_log_entry(alert='monitor', code='INVALID_ZIP', message='Invalid zip file', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
                logger.error(entry)
                send_to_fluentd(entry)
                return jsonify({'error': 'Invalid zip file'}), 400
            if bad:
                entry = make_log_entry(alert='monitor', code='ILLEGAL_ZIP', message='Illegal zip file', endpoint=endpoint, extra={**log_context, 'illegal_files': bad}, correlation_id=correlation_id)
                logger.error(entry)
                send_to_fluentd(entry)
                os.remove(tmp_zip_path)
                return jsonify({'error': f'Illegal file found: {bad[0]}. Zip file must only contain gif, jpg, jpeg, or png image files'}), 400
            # Generate output zip name
            output_zip_name = safe_zip_filename(image.filename)
            # Produce Kafka message
            try:
                user_id = None
                if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                    user_id = getattr(current_user, 'id', None)
                logger.info(f"Kafka zip-requests: current_user.is_authenticated={getattr(current_user, 'is_authenticated', None)}, current_user.id={getattr(current_user, 'id', None)}, user_id={user_id}")
                kafka_message = json.dumps({
                    'correlationId': correlation_id,
                    'filename': image.filename,
                    'percent': percent,
                    'user_id': user_id,
                    'upload_path': tmp_zip_path,
                    'output_zip_name': output_zip_name
                })
                kafka_producer.produce(KAFKA_ZIP_TOPIC, kafka_message.encode('utf-8'))
                kafka_producer.flush()
            except Exception as e:
                entry = make_log_entry(alert='emergency', code='A2', message=f'Kafka error: {str(e)}', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
                logger.error(entry)
                send_to_fluentd(entry)
                os.remove(tmp_zip_path)
                return jsonify({'error': 'Error A2: Unable to process zip files. Try again later'}), 500
            # Create a Request record for the zip job
            req = Request(
                user_id=user_id,
                request_created=datetime.datetime.now(datetime.UTC),
                correlation_id=correlation_id,
                customer_filename=image.filename,
                resized_filename=None,  # Will be set when processing is done
                status='Pending',
                failure_reason=None,
                type='zip',
                reduce_to_percent=int(percent) if percent else None,
                original_filesize=os.path.getsize(tmp_zip_path) if os.path.exists(tmp_zip_path) else None,
                new_filesize=None
            )
            db.session.add(req)
            db.session.commit()
        except Exception as e:
            entry = make_log_entry(alert='monitor', code='A2', message=f'Error saving zip request to DB: {str(e)}', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
            logger.error(entry)
            send_to_fluentd(entry)
            os.remove(tmp_zip_path)
            return jsonify({'error': 'Error A2: Unable to process zip files. Try again later'}), 500
        entry = make_log_entry(alert='info', code='ZIP_REQUESTED', message='Zip processing requested', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
        logger.info(entry)
        send_to_fluentd(entry)
        return jsonify({'message': 'Zip file accepted for processing', 'correlation_id': correlation_id}), 202
    else:
        entry = make_log_entry(alert='monitor', code='INVALID_FILE_TYPE', message='Invalid file type', endpoint=endpoint, extra=log_context, correlation_id=correlation_id)
        logger.warning(entry)
        send_to_fluentd(entry)
        RESIZE_ERROR_COUNT.labels(error_type='invalid_file_type').inc()
        return jsonify({'error': 'Only image files accepted. Upload a gif, jpg, jpeg or png' + (' or zip' if ENABLE_ZIP else '')}), 400

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    """
    Download a resized image by filename.
    ---
    parameters:
      - in: path
        name: filename
        type: string
        required: true
        description: The name of the resized image file to download.
    responses:
      200:
        description: The image file will be downloaded.
      404:
        description: File not found.
    """
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/download-zip/<filename>', methods=['GET'])
def download_zip(filename):
    """
    Download a processed zip file by filename.
    ---
    parameters:
      - in: path
        name: filename
        type: string
        required: true
        description: The name of the processed zip file to download.
    responses:
      200:
        description: The zip file will be downloaded.
      404:
        description: File not found.
    """
    # This should match the output dir used by the zip-processor
    output_dir = os.environ.get('ZIP_PROCESSOR_OUTPUT_DIR', '../zip-processing/output')
    file_path = os.path.join(output_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    return send_from_directory(output_dir, filename, as_attachment=True)

@app.route('/metrics')
def metrics():
    """
    Prometheus metrics endpoint.
    ---
    responses:
      200:
        description: Prometheus metrics in plain text format.
    """
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}


# Database configuration using environment variables
DB_USER = os.environ.get('DB_USER', 'imguser')
DB_PASS = os.environ.get('DB_PASS')  # No default
DB_HOST = os.environ.get('DB_HOST')  # No default
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'image_processing')

USE_DATABASE = DB_PASS is not None and DB_HOST is not None

print(f"-----------------------------------------------------------------------------")
print(f"Connect to database {'ENABLED' if USE_DATABASE else 'DISABLED'}")
print(f"(Must be ENABLED for zip processing or user login or logged-in user requests)")
print(f"-----------------------------------------------------------------------------")
print()

if USE_DATABASE:
    from auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    bcrypt.init_app(app)
    migrate = Migrate(app, db)
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/my-requests', methods=['GET'])
    @login_required
    def my_requests():
        """
        Get all image processing requests for the authenticated user.
        ---
        description: |
          Returns a list of image processing requests for the authenticated user.
          
          **Requires:** Database to be enabled and user to be logged in.
        responses:
          200:
            description: List of requests for the user.
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  request_created:
                    type: string
                  customer_filename:
                    type: string
                  resized_filename:
                    type: string
                  reduce_to_percent:
                    type: integer
                  original_filesize:
                    type: integer
                  new_filesize:
                    type: integer
                  status:
                    type: string
                  expiry:
                    type: string
                  correlation_id:
                    type: string
                  original_resolution:
                    type: string
                  resized_resolution:
                    type: string
                  failure_reason:
                    type: string
                  type:
                    type: string
          401:
            description: Unauthorized (user not logged in)
        """
        from models import Request
        requests = Request.query.filter_by(user_id=current_user.id).order_by(Request.request_created.desc()).all()
        result = []
        for req in requests:
            result.append({
                'id': req.id,
                'request_created': req.request_created.isoformat() if req.request_created else None,
                'customer_filename': req.customer_filename,
                'resized_filename': req.resized_filename,
                'reduce_to_percent': req.reduce_to_percent,
                'original_filesize': req.original_filesize,
                'new_filesize': req.new_filesize,
                'status': req.status,
                'expiry': req.expiry.isoformat() if req.expiry else None,
                'correlation_id': req.correlation_id,
                'original_resolution': req.original_resolution,
                'resized_resolution': req.resized_resolution,
                'failure_reason': req.failure_reason,
                'type': req.type,
            })
        return jsonify(result), 200

@app.route('/zip-status/<correlation_id>', methods=['GET'])
def zip_status(correlation_id):
    """
    Get the status of a zip processing job by correlation ID.
    ---
    description: |
      Returns the status and output filename for a zip processing job by correlation ID.
      
      **Requires:** Database to be enabled.
    parameters:
      - in: path
        name: correlation_id
        type: string
        required: true
        description: The correlation ID for the zip processing job.
    responses:
      200:
        description: Status and output filename for the zip job.
      404:
        description: Not found.
    """
    # Query the Request table for a zip job with the given correlation_id
    req = Request.query.filter_by(correlation_id=correlation_id, type='zip').first()
    if not req:
        return jsonify({'error': 'Not found'}), 404
    # Return relevant info for the frontend
    return jsonify({
        'correlation_id': req.correlation_id,
        'status': req.status,
        'output_filename': req.resized_filename,
        'failure_reason': req.failure_reason
    }), 200

# ---
# Filename handling utilities for secure, unique, and robust file storage
#
# All uploaded and processed files are saved with randomized, sanitized filenames to prevent collisions,
# directory traversal, and information leakage. These functions should be used for any file that is saved
# or referenced by the backend. The random prefix ensures uniqueness, and the sanitization removes any
# potentially dangerous characters. The reduced and zip filename functions ensure consistent naming for
# processed outputs.
#
def random_prefix(length=6):
    """Generate a random alphanumeric prefix for filenames (default: 6 chars)."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def safe_upload_filename(filename):
    """
    Generate a safe, unique filename for uploads by adding a random prefix and sanitizing the name.
    - Truncates the base name to 40 chars and preserves the extension.
    - Removes any unsafe characters (only A-Z, a-z, 0-9, dot, underscore, dash allowed).
    - Prepends a random prefix to ensure uniqueness and prevent collisions.
    - Example: 'my cat.png' -> 'A1b2C3_my_cat.png'
    - Always use this before saving any uploaded file.
    """
    filename = os.path.basename(filename)
    if '.' in filename:
        base, ext = filename.rsplit('.', 1)
        ext = '.' + ext
    else:
        base, ext = filename, ''
    base = re.sub(r'[^A-Za-z0-9._-]', '_', base)
    base = base[:40]
    prefix = random_prefix()
    return f"{prefix}_{base}{ext}"

def safe_reduced_filename(upload_filename):
    """
    Generate a filename for the reduced (resized) image, based on the upload filename.
    - Inserts '_reduced' before the extension, or at the end if no extension.
    - Ensures no double '_reduced' if already present.
    - Example: 'A1b2C3_my_cat.png' -> 'A1b2C3_my_cat_reduced.png'
    - Always use this for naming resized images.
    """
    if '.' in upload_filename:
        base, ext = upload_filename.rsplit('.', 1)
        if base.endswith('_reduced'):
            return f"{base}.{ext}"
        return f"{base}_reduced.{ext}"
    else:
        if upload_filename.endswith('_reduced'):
            return upload_filename
        return f"{upload_filename}_reduced"

def safe_zip_filename(filename):
    """
    Generate a safe, unique filename for zip uploads by adding a random prefix and sanitizing the name.
    - Truncates the base name to 40 chars and ensures .zip extension.
    - Removes any unsafe characters (only A-Z, a-z, 0-9, dot, underscore, dash allowed).
    - Prepends a random prefix to ensure uniqueness and prevent collisions.
    - Example: 'holiday photos.zip' -> 'A1b2C3_holiday_photos.zip'
    - Always use this before saving or referencing any zip file.
    """
    filename = os.path.basename(filename)
    if filename.lower().endswith('.zip'):
        base = filename[:-4]
        ext = '.zip'
    else:
        base, ext = filename, '.zip'
    base = re.sub(r'[^A-Za-z0-9._-]', '_', base)
    base = base[:40]
    prefix = random_prefix()
    return f"{prefix}_{base}{ext}"
# ---

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
