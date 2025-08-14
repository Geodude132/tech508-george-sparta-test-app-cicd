from .config import FLUENTD_URL, PROCESSING_OUTPUT_DIR
from .logging_utils import logger, make_log_entry, send_to_fluentd
from .image_processing import extract_and_resize
from .consumer import start_consumer
from confluent_kafka import Producer
import os
import shutil
import json

KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_PROCESSED_TOPIC = os.environ.get('KAFKA_PROCESSED_TOPIC', 'zip-processed')
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

def send_zip_processed_message(correlation_id, output_filename=None, status="Success", failure_reason=None):
    message = {
        "correlationId": correlation_id,
        "status": status,
        "output_filename": output_filename,
        "failure_reason": failure_reason,
    }
    producer.produce(KAFKA_PROCESSED_TOPIC, json.dumps(message).encode('utf-8'))
    producer.flush()

def process_zip_message(data):
    correlation_id = data.get('correlationId')
    zip_path = data.get('upload_path')
    percent = int(data.get('percent', 50))
    user_id = data.get('user_id')
    output_zip_name = data.get('output_zip_name')
    try:
        logger.info(f"Processing zip for correlationId={correlation_id}")
        entry = make_log_entry(alert='info', code='ZIP_PROCESSING_STARTED', message='Zip processing started', endpoint='zip-processor', correlation_id=correlation_id)
        logger.info(entry)
        send_to_fluentd(entry, FLUENTD_URL)
        output_zip, extracted_dir = extract_and_resize(zip_path, PROCESSING_OUTPUT_DIR, percent, correlation_id, output_zip_name=output_zip_name)
        entry = make_log_entry(alert='info', code='ZIP_SUCCESS', message='Zip file processed', endpoint='zip-processor', correlation_id=correlation_id, extra={'output_zip': output_zip})
        logger.info(entry)
        send_to_fluentd(entry, FLUENTD_URL)
        send_zip_processed_message(correlation_id, output_filename=output_zip_name, status="Success")
        # Clean up extracted images, but keep output zip
        shutil.rmtree(extracted_dir, ignore_errors=True)
    except Exception as e:
        # Try to extract filename from the exception string
        error_str = str(e)
        image_name = None
        if 'zipfile.ZipExtFile' in error_str and 'name=' in error_str:
            import re
            match = re.search(r"name='([^']+)'", error_str)
            if match:
                image_name = match.group(1)
        if image_name:
            friendly_reason = f"Error resizing image {image_name}"
        else:
            friendly_reason = f"Error resizing image in zip"
        entry = make_log_entry(alert='monitor', code='ZIP_FAIL', message=f'Zip file failure: {friendly_reason}', endpoint='zip-processor', correlation_id=correlation_id, extra={'error_on_image': friendly_reason})
        logger.error(entry)
        send_to_fluentd(entry, FLUENTD_URL)
        send_zip_processed_message(correlation_id, status="Failure", failure_reason=friendly_reason)
        # Clean up on error
        if 'extracted_dir' in locals():
            shutil.rmtree(extracted_dir, ignore_errors=True)
        if 'output_zip' in locals() and os.path.exists(output_zip):
            os.remove(output_zip)

def main():
    start_consumer(process_zip_message, FLUENTD_URL)

if __name__ == "__main__":
    main()
