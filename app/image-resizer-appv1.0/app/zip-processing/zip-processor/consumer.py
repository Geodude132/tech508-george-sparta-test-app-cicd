import json
from confluent_kafka import Consumer
from .config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_ZIP_TOPIC
from .logging_utils import logger, make_log_entry, send_to_fluentd

def start_consumer(process_zip_callback, fluentd_url):
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'zip-processor-group',
        'auto.offset.reset': 'earliest',
    })
    consumer.subscribe([KAFKA_ZIP_TOPIC])
    logger.info(f"Listening to Kafka topic: {KAFKA_ZIP_TOPIC}")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Kafka error: {msg.error()}")
            continue
        try:
            data = json.loads(msg.value().decode('utf-8'))
            process_zip_callback(data)
        except Exception as e:
            entry = make_log_entry(alert='monitor', code='CONSUMER_ERROR', message=str(e), endpoint='kafka', correlation_id=None)
            logger.error(entry)
            send_to_fluentd(entry, fluentd_url)
