import pino from 'pino';

let shouldSendLogs = false;
function setFluentdLogging(enabled) {
  shouldSendLogs = enabled;
}

const node = window.location.hostname || 'browser';
const component = 'Image-Resizer React frontend';

function fallbackUUID() {
  // Simple RFC4122 version 4 compliant UUID generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : ((r & 0x3) | 0x8);
    return v.toString(16);
  });
}

function makeLogEntry(fields = {}) {
  const now = new Date();
  let correlationId;
  if (window.__correlationId) {
    correlationId = window.__correlationId;
  } else {
    if (window.crypto && window.crypto.randomUUID) {
      correlationId = window.crypto.randomUUID();
    } else {
      correlationId = fallbackUUID();
    }
    window.__correlationId = correlationId;
  }
  return {
    timestamp: now.getTime(),
    date: now.toUTCString(),
    component,
    node,
    correlationId,
    ...fields
  };
}

const logger = pino({
  level: 'info',
  browser: {
    asObject: true,
    transmit: {
      level: 'info',
      send: (level, logEvent) => {
        if (shouldSendLogs) {
          fetch('http://localhost:9880/frontend.logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(logEvent)
          }).catch((err) => {
            // If enabled, let fetch errors surface; otherwise, ignore
            if (shouldSendLogs) throw err;
          });
        }
      }
    }
  }
});

export { logger, makeLogEntry, setFluentdLogging };
