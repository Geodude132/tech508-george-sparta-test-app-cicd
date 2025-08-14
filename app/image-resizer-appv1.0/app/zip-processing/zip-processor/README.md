# Zip Processor Service

This service consumes messages from the `zip-requests` Kafka topic, processes image zip files, resizes images, and logs events to Fluentd.

## Dependencies

* Requires Kafka to be running

  1. cd into the `zip-processor/kafka` folder
  2. Run:
     ```
     docker compose up -d
     ```

<br>

## Run the "zip-processor" service

1. **Activate the venv**

    If using Linux, Mac terminal, or a Git Bash window:
    ```bash
    source .venv/Scripts/activate
    ```

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables/configuration:**
   - `KAFKA_BOOTSTRAP_SERVERS` (default: `localhost:9092`)
   - `KAFKA_ZIP_TOPIC` (default: `zip-requests`)
   - `FLUENTD_URL` (default: `http://localhost:9880/zip-processor.logs`)
   - `PROCESSING_OUTPUT_DIR` (default: `output/`)

3. **Run the processor:**
   
   1. cd into the parent folder
   2. Run:
      ```bash
      python -m processor.main
      ```

## Folder Structure

- `main.py` - Entry point
- `config.py` - Loads configuration
- `consumer.py` - Kafka consumer logic
- `image_processing.py` - Image extraction, resizing, and zipping
- `logging_utils.py` - Fluentd logging helpers
- `utils.py` - Shared helpers

## Logging

All logs are sent to Fluentd in the same format as the backend, including `correlationId` and extra metadata.

---

For more details, see the code comments in each file.
