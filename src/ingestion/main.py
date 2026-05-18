import os
import re
import logging
import base64
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict

from google.cloud import storage, bigquery
from google.api_core import exceptions
import pandas as pd
from validator import validate_dataframe, BQ_SCHEMA_REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
)
logger = logging.getLogger(__name__)

app = FastAPI()


# --- Health Check ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# --- Exception Handlers ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred while processing the file.",
                "details": {}
            }
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "BAD_REQUEST",
                "message": str(exc),
                "details": {}
            }
        }
    )


@app.exception_handler(FileNotFoundError)
async def not_found_error_handler(request: Request, exc: FileNotFoundError):
    logger.error(f"File not found: {exc}")
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "The requested file could not be found.",
                "details": {}
            }
        }
    )


# --- Clients ---
storage_client = storage.Client()
bq_client = bigquery.Client()

# --- Configuration ---
PROJECT_ID = os.environ.get("PROJECT_ID")
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET")
PROCESSING_BUCKET = os.environ.get("PROCESSING_BUCKET")
BRONZE_DATASET = os.environ.get("BRONZE_DATASET")
SCHEMA_BUCKET = os.environ.get("SCHEMA_BUCKET")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET")
ARCHIVE_BUCKET = os.environ.get("ARCHIVE_BUCKET")

BQ_LOAD_TIMEOUT = 300  # seconds


# --- Models ---
class PubSubMessageData(BaseModel):
    data: Optional[str] = None
    attributes: Optional[Dict[str, str]] = None
    messageId: Optional[str] = None
    publishTime: Optional[str] = None


class PubSubMessage(BaseModel):
    message: PubSubMessageData
    subscription: str


# --- File Processing Helpers ---

def _acquire_processing_lock(bucket_name: str, file_name: str):
    """
    Atomically move a file from landing to processing bucket.
    Returns (processing_blob, original_generation) or (None, None) if already processed.
    """
    bucket = storage_client.bucket(bucket_name)
    original_blob = bucket.get_blob(file_name)

    if not original_blob:
        logger.info(f"File {file_name} not found in {bucket_name}. Likely already processed.")
        return None, None

    processing_bkt = storage_client.bucket(PROCESSING_BUCKET)

    try:
        blob = bucket.copy_blob(
            original_blob,
            processing_bkt,
            new_name=file_name,
            if_source_generation_match=original_blob.generation,
            if_generation_match=0
        )
        original_blob.delete(if_generation_match=original_blob.generation)
        return blob, blob.generation
    except (exceptions.NotFound, exceptions.PreconditionFailed):
        logger.info(f"File {file_name} concurrently moved to processing or deleted.")
        return None, None


def _resolve_table_name(file_name: str) -> str:
    """Extract and sanitize the target table name from the file path."""
    base_name = os.path.basename(file_name)
    parts = file_name.split('/')
    if len(parts) >= 2:
        table_name = parts[0]
    else:
        table_name = base_name.split('.')[0]

    return re.sub(r'[^a-zA-Z0-9_]', '_', table_name)


def _validate_file(blob, file_name: str, table_name: str):
    """
    Validate the file content against its schema.
    Returns (total_valid, total_invalid).
    """
    total_valid = 0
    total_invalid = 0

    with blob.open("rt") as f:
        try:
            if file_name.endswith(".csv"):
                iterator = pd.read_csv(f, chunksize=10000)
            elif file_name.endswith((".jsonl", ".json")):
                iterator = pd.read_json(f, lines=True, chunksize=10000)
            else:
                logger.warning(f"Unsupported file format: {file_name}")
                return 0, 1

            for chunk_df in iterator:
                valid_df, invalid_df = validate_dataframe(
                    chunk_df, table_name,
                    storage_client=storage_client,
                    schema_bucket=SCHEMA_BUCKET
                )

                if not invalid_df.empty:
                    total_invalid += len(invalid_df)
                    break  # All-or-nothing

                total_valid += len(valid_df)
        except Exception as e:
            logger.error(f"Failed to parse file {file_name}: {e}")
            return 0, 1

    return total_valid, total_invalid


def _quarantine_file(blob, processing_bkt, file_name: str):
    """Move a file from processing to quarantine bucket."""
    quarantine_bkt = storage_client.bucket(QUARANTINE_BUCKET)
    quarantine_blob_name = f"{file_name.replace('/', '_')}_{blob.generation}"
    try:
        processing_bkt.copy_blob(
            blob, quarantine_bkt,
            new_name=quarantine_blob_name,
            if_source_generation_match=blob.generation
        )
        blob.delete(if_generation_match=blob.generation)
    except (exceptions.NotFound, exceptions.PreconditionFailed):
        pass  # Another instance might have processed it concurrently


def _load_to_bigquery(blob, processing_bkt, file_name: str, table_name: str, table_id: str):
    """
    Stage the file and load it into BigQuery.
    Returns a result dict with status and record counts.
    """
    staging_bkt = storage_client.bucket(STAGING_BUCKET)
    staging_blob_name = f"{file_name.replace('/', '_')}_{blob.generation}"

    # Copy to staging
    try:
        staging_blob = processing_bkt.copy_blob(
            blob, staging_bkt,
            new_name=staging_blob_name,
            if_source_generation_match=blob.generation
        )
    except (exceptions.NotFound, exceptions.PreconditionFailed):
        logger.info(f"File {file_name} deleted or concurrently modified before staging copy.")
        return {"status": "already_processed_or_modified"}

    # Build BQ load config
    safe_job_name = re.sub(r'[^a-zA-Z0-9_-]', '_', file_name)
    job_id = f"ingest_{safe_job_name}_{blob.generation}"
    is_json = file_name.endswith((".jsonl", ".json"))

    bq_schema = BQ_SCHEMA_REGISTRY.get(table_name)

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        schema_update_options=["ALLOW_FIELD_ADDITION"],
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON if is_json else bigquery.SourceFormat.CSV,
        skip_leading_rows=0 if is_json else 1
    )

    if bq_schema:
        job_config.schema = bq_schema
    else:
        job_config.autodetect = True

    uri = f"gs://{STAGING_BUCKET}/{staging_blob_name}"

    try:
        job = bq_client.load_table_from_uri(uri, table_id, job_config=job_config, job_id=job_id)
        job.result(timeout=BQ_LOAD_TIMEOUT)
        logger.info(f"Loaded rows into {table_id} via job {job_id}")
    except Exception as e:
        error_details = job.errors if 'job' in locals() and hasattr(job, 'errors') else 'none'
        logger.error(f"Failed BQ Load for {file_name}: {e}. Errors: {error_details}")

        # Quarantine on BQ failure
        _quarantine_file(blob, processing_bkt, file_name)
        try:
            staging_bkt.blob(staging_blob_name).delete()
        except exceptions.NotFound:
            pass

        return {
            "status": "quarantined_bq_failure",
            "valid_records_loaded": 0,
            "invalid_records": 0
        }

    return {"status": "bq_loaded", "staging_blob_name": staging_blob_name}


def _archive_file(blob, processing_bkt, staging_blob_name: str):
    """Move file from processing to archive and clean up staging."""
    archive_bkt = storage_client.bucket(ARCHIVE_BUCKET)
    try:
        processing_bkt.copy_blob(blob, archive_bkt, if_source_generation_match=blob.generation)
        blob.delete(if_generation_match=blob.generation)
    except (exceptions.NotFound, exceptions.PreconditionFailed):
        pass

    staging_bkt = storage_client.bucket(STAGING_BUCKET)
    try:
        staging_bkt.blob(staging_blob_name).delete()
    except exceptions.NotFound:
        pass


# --- Main Processing Logic ---

def process_file(bucket_name: str, file_name: str):
    """
    Process a single file: acquire lock, validate, load to BQ, archive.
    Designed for idempotency — safe to call multiple times for the same file.
    """
    # Step 1: Acquire processing lock (atomic move from landing)
    blob, generation = _acquire_processing_lock(bucket_name, file_name)
    if blob is None:
        return {"status": "already_processed"}

    processing_bkt = storage_client.bucket(PROCESSING_BUCKET)
    table_name = _resolve_table_name(file_name)
    table_id = f"{PROJECT_ID}.{BRONZE_DATASET}.{table_name}"

    # Step 2: Validate the file
    total_valid, total_invalid = _validate_file(blob, file_name, table_name)

    # Step 3: Route based on validation result
    if total_invalid > 0:
        _quarantine_file(blob, processing_bkt, file_name)
        logger.info(f"Ingestion complete for {file_name}: file is invalid. Moved to quarantine.")
        return {
            "status": "quarantined",
            "valid_records_loaded": 0,
            "invalid_records": total_invalid
        }

    if total_valid > 0:
        result = _load_to_bigquery(blob, processing_bkt, file_name, table_name, table_id)
        if result["status"] == "bq_loaded":
            _archive_file(blob, processing_bkt, result["staging_blob_name"])
            logger.info(f"Ingestion complete for {file_name}. File moved to archive.")
            return {
                "status": "success",
                "valid_records_loaded": total_valid,
                "invalid_records": 0
            }
        return result

    # Handle empty files
    logger.warning(f"File {file_name} is empty. Archiving immediately.")
    _archive_file(blob, processing_bkt, "")
    return {
        "status": "empty",
        "valid_records_loaded": 0,
        "invalid_records": 0
    }


# --- API Endpoint ---

@app.post("/v1/pubsub/messages")
async def ingest_pubsub(request: PubSubMessage):
    if request.message.data:
        decoded_data = base64.b64decode(request.message.data).decode("utf-8")
        event_payload = json.loads(decoded_data)
        bucket_name = event_payload.get("bucket")
        file_name = event_payload.get("name")
    else:
        bucket_name = request.message.attributes.get("bucketId") if request.message.attributes else None
        file_name = request.message.attributes.get("objectId") if request.message.attributes else None

    if not bucket_name or not file_name:
        raise ValueError("Missing bucket or name in Pub/Sub message")

    # Ignore folder creation events
    if file_name.endswith('/'):
        logger.info("Ignoring folder creation event.")
        return {"status": "ignored"}

    return process_file(bucket_name, file_name)
