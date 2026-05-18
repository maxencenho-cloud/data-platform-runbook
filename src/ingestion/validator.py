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
    """
    valid_records = []
    invalid_records = []

    # Lazy load schema if not in registry
    if table_name not in SCHEMA_REGISTRY:
        schema = load_schema_from_gcs(storage_client, schema_bucket, table_name)
        if schema:
            SCHEMA_REGISTRY[table_name] = schema

    schema = SCHEMA_REGISTRY.get(table_name)

    if not schema:
        # If no schema is found, quarantine all records
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            row_dict['quarantine_reason'] = f"Schema not found for table: {table_name}"
            invalid_records.append(row_dict)
        return pd.DataFrame(), pd.DataFrame(invalid_records)

    for index, row in df.iterrows():
        try:
            # Convert NaN to None for nullable field support
            row_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
            schema(**row_dict)
            valid_records.append(row)
        except ValidationError as e:
            row_dict = row.to_dict()
            row_dict['quarantine_reason'] = str(e)
            invalid_records.append(row_dict)

    valid_df = pd.DataFrame(valid_records)
    invalid_df = pd.DataFrame(invalid_records)

    return valid_df, invalid_df
