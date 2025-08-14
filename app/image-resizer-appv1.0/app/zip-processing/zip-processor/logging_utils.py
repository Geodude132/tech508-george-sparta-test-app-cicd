import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("zip-processor")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

import requests

def send_to_fluentd(log_entry, fluentd_url):
    try:
        requests.post(fluentd_url, json=log_entry, timeout=0.5)
    except Exception:
        pass

def make_log_entry(alert=None, code=None, message=None, endpoint=None, extra=None, correlation_id=None):
    import socket, uuid, datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    log_entry = {
        'timestamp': int(now.timestamp() * 1000),
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'alert': alert,
        'component': 'Zip-Processor',
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
