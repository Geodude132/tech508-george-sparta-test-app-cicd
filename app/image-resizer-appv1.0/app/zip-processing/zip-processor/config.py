import os

KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_ZIP_TOPIC = os.environ.get('KAFKA_ZIP_TOPIC', 'zip-requests')
FLUENTD_URL = os.environ.get('FLUENTD_URL', 'http://localhost:9880/zip-processor.logs')
PROCESSING_OUTPUT_DIR = os.environ.get('PROCESSING_OUTPUT_DIR', 'output/')

os.makedirs(PROCESSING_OUTPUT_DIR, exist_ok=True)
