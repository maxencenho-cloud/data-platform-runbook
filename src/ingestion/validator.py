from pydantic import ValidationError, create_model
from typing import Optional
import yaml
from google.cloud import bigquery

# Schema caches — populated on first use, persist for the lifetime of the process
SCHEMA_REGISTRY = {}
BQ_SCHEMA_REGISTRY = {}

TYPE_MAPPING = {
    "int": int,
    "str": str,
    "float": float,
    "bool": bool,
    "date": str,      # Validated as string, BQ handles date parsing
    "datetime": str,   # Validated as string, BQ handles timestamp parsing
}

BQ_TYPE_MAPPING = {
    "int": "INTEGER",
    "str": "STRING",
    "float": "FLOAT",
    "bool": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMP",
}


def load_schema_from_gcs(storage_client, schema_bucket: str, table_name: str):
    """
    Download and parse the schema YAML from GCS, building a dynamic Pydantic model.
    Returns the Pydantic model class, or None if no schema is found.
    """
    if not schema_bucket:
        return None

    bucket = storage_client.bucket(schema_bucket)
    blob = bucket.blob(f"bronze/{table_name}.yaml")

    if not blob.exists():
        return None

    yaml_content = blob.download_as_text()
    schema_def = yaml.safe_load(yaml_content)

    if not schema_def or 'fields' not in schema_def:
        return None

    fields = {}
    bq_fields = []

    for field in schema_def['fields']:
        field_name = field['name']
        field_type = TYPE_MAPPING.get(field.get('type', 'str'), str)
        is_nullable = field.get('nullable', False)
        bq_mode = "NULLABLE" if is_nullable else "REQUIRED"

        if is_nullable:
            fields[field_name] = (Optional[field_type], None)
        else:
            fields[field_name] = (field_type, ...)

        bq_fields.append(bigquery.SchemaField(
            field_name,
            BQ_TYPE_MAPPING.get(field.get('type', 'str'), "STRING"),
            mode=bq_mode,
            description=field.get('description', '')
        ))

    BQ_SCHEMA_REGISTRY[table_name] = bq_fields

    return create_model(f"{table_name}_schema", **fields)


def get_schema(table_name: str, storage_client=None, schema_bucket=None):
    """Get the Pydantic schema for a table, loading from GCS on first access."""
    if table_name not in SCHEMA_REGISTRY:
        schema = load_schema_from_gcs(storage_client, schema_bucket, table_name)
        if schema:
            SCHEMA_REGISTRY[table_name] = schema

    return SCHEMA_REGISTRY.get(table_name)


def validate_record(record: dict, schema) -> Optional[str]:
    """
    Validate a single record against a Pydantic schema.
    Returns None if valid, error message string if invalid.

    Empty strings are converted to None to handle CSV empty cells —
    csv.DictReader returns "" for missing values, but Pydantic Optional
    fields expect Python None.
    """
    try:
        clean = {k: (None if v == "" else v) for k, v in record.items()}
        schema(**clean)
        return None
    except ValidationError as e:
        return str(e)
