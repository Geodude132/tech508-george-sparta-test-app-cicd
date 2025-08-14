import os
import json
import time
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Request(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String)
    type = Column(String)
    status = Column(String)
    resized_filename = Column(String)
    failure_reason = Column(String)
    new_filesize = Column(Integer)

# Database connection
DB_USER = os.environ.get('DB_USER', 'imguser')
DB_PASS = os.environ.get('DB_PASS')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'image_processing')

USE_DATABASE = DB_PASS is not None and DB_HOST is not None

print(f"---------------------------------------------------------------------------------")
print(f"Connect to database {'ENABLED' if USE_DATABASE else 'DISABLED'}")
print(f"(Must be ENABLED for zip-processed-listener to update requests table in database)")
print(f"---------------------------------------------------------------------------------")
print()

DB_URL = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

# Kafka config
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_PROCESSED_TOPIC = os.environ.get('KAFKA_PROCESSED_TOPIC', 'zip-processed')
GROUP_ID = os.environ.get('KAFKA_PROCESSED_GROUP_ID', 'zip-processed-listener')

def start_listener():
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': GROUP_ID,
        'auto.offset.reset': 'earliest',
    })
    consumer.subscribe([KAFKA_PROCESSED_TOPIC])
    print(f"[zip-processed-listener] Listening to {KAFKA_PROCESSED_TOPIC} ...")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue
        try:
            data = json.loads(msg.value().decode('utf-8'))
            correlation_id = data.get('correlationId')
            status = data.get('status')
            output_filename = data.get('output_filename')
            failure_reason = data.get('failure_reason')
            session = Session()
            req = session.query(Request).filter_by(correlation_id=correlation_id, type='zip').first()
            if req:
                req.status = 'Success' if status == 'Success' else 'Failure'
                if status == 'Success' and output_filename:
                    req.resized_filename = output_filename
                    # Set new_filesize to the size of the processed zip file
                    output_dir = os.environ.get('PROCESSING_OUTPUT_DIR', 'output/')
                    output_path = os.path.join(output_dir, output_filename) if output_filename else None
                    if output_path and os.path.exists(output_path):
                        req.new_filesize = os.path.getsize(output_path)
                if status == 'Failure' and failure_reason:
                    req.failure_reason = failure_reason
                session.commit()
                print(f"[zip-processed-listener] Updated request {correlation_id} to {req.status}")
            else:
                print(f"[zip-processed-listener] No matching request for correlation_id {correlation_id}")
            session.close()
        except Exception as e:
            print(f"[zip-processed-listener] Error processing message: {e}")
    consumer.close()

if __name__ == "__main__":
    start_listener()
