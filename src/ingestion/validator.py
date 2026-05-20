from pydantic import BaseModel, ValidationError, create_model
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import yaml
from google.cloud import bigquery

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
    Attempts to download and parse the schema YAML from GCS, building a dynamic Pydantic model.
    Supports nullable fields and enriched schema format (version, description).
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
            # Optional field: can be None
            fields[field_name] = (Optional[field_type], None)
        else:
            # Required field
            fields[field_name] = (field_type, ...)

        bq_fields.append(bigquery.SchemaField(
            field_name,
            BQ_TYPE_MAPPING.get(field.get('type', 'str'), "STRING"),
            mode=bq_mode,
            description=field.get('description', '')
        ))

    BQ_SCHEMA_REGISTRY[table_name] = bq_fields

    # Dynamically create and return the Pydantic model
    return create_model(f"{table_name}_schema", **fields)


def validate_dataframe(df: pd.DataFrame, table_name: str, storage_client=None, schema_bucket=None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates a DataFrame against the schema corresponding to table_name.
    Lazy loads the schema from GCS if it is not in the registry.
    Returns a tuple of (valid_df, invalid_df).
    Optimized for high performance using records and fail-fast short-circuiting.
    """
    # Lazy load schema if not in registry
    if table_name not in SCHEMA_REGISTRY:
        schema = load_schema_from_gcs(storage_client, schema_bucket, table_name)
        if schema:
            SCHEMA_REGISTRY[table_name] = schema

    schema = SCHEMA_REGISTRY.get(table_name)

    if not schema:
        # If no schema is found, quarantine all records quickly
        records = df.to_dict(orient='records')
        for record in records:
            record['quarantine_reason'] = f"Schema not found for table: {table_name}"
        return pd.DataFrame(), pd.DataFrame(records)

    # Convert DataFrame to records (dict list) for massive speedup over iterrows()
    records = df.to_dict(orient='records')
    valid_records = []

    for record in records:
        try:
            # Clean up NaN to None for nullable field compatibility in Pydantic
            clean_record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
            schema(**clean_record)
            valid_records.append(record)
        except ValidationError as e:
            # Short-circuit immediately on first validation failure (All-or-Nothing)
            record['quarantine_reason'] = str(e)
            return pd.DataFrame(), pd.DataFrame([record])

    return pd.DataFrame(valid_records), pd.DataFrame()
