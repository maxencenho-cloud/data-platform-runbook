"""Unit tests for the validator module."""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from tests.mocks import MockStorageClient, MockBucket, MockBlob

# Reset global registries before importing to avoid test pollution
import sys
import importlib


@pytest.fixture(autouse=True)
def reset_registries():
    """Reset global schema registries before each test."""
    if 'validator' in sys.modules:
        importlib.reload(sys.modules['validator'])
    yield


@pytest.fixture
def validator():
    import validator
    validator.SCHEMA_REGISTRY.clear()
    validator.BQ_SCHEMA_REGISTRY.clear()
    return validator


class TestLoadSchemaFromGCS:
    """Tests for schema loading from GCS."""

    def test_returns_none_when_no_schema_bucket(self, validator):
        result = validator.load_schema_from_gcs(MagicMock(), None, "test_table")
        assert result is None

    def test_returns_none_when_blob_not_found(self, validator):
        client = MockStorageClient()
        bucket = MockBucket("schemas")
        client._buckets["schemas"] = bucket
        result = validator.load_schema_from_gcs(client, "schemas", "nonexistent_table")
        assert result is None

    def test_loads_valid_schema_and_creates_model(self, validator, sample_schema_yaml):
        blob = MockBlob("bronze/test_table.yaml", content=sample_schema_yaml)
        bucket = MockBucket("schemas", blobs={"bronze/test_table.yaml": blob})
        client = MockStorageClient(buckets={"schemas": bucket})

        model = validator.load_schema_from_gcs(client, "schemas", "test_table")

        assert model is not None
        assert "test_table" in validator.BQ_SCHEMA_REGISTRY
        assert len(validator.BQ_SCHEMA_REGISTRY["test_table"]) == 3

    def test_returns_none_for_empty_yaml(self, validator):
        blob = MockBlob("bronze/empty.yaml", content="")
        bucket = MockBucket("schemas", blobs={"bronze/empty.yaml": blob})
        client = MockStorageClient(buckets={"schemas": bucket})

        result = validator.load_schema_from_gcs(client, "schemas", "empty")
        assert result is None

    def test_returns_none_for_yaml_without_fields(self, validator):
        blob = MockBlob("bronze/bad.yaml", content="name: test\nversion: 1")
        bucket = MockBucket("schemas", blobs={"bronze/bad.yaml": blob})
        client = MockStorageClient(buckets={"schemas": bucket})

        result = validator.load_schema_from_gcs(client, "schemas", "bad")
        assert result is None


class TestValidateDataframe:
    """Tests for DataFrame validation against schemas."""

    def _setup_schema(self, validator, sample_schema_yaml):
        blob = MockBlob("bronze/test_table.yaml", content=sample_schema_yaml)
        bucket = MockBucket("schemas", blobs={"bronze/test_table.yaml": blob})
        return MockStorageClient(buckets={"schemas": bucket})

    def test_valid_dataframe_returns_all_valid(self, validator, sample_dataframe, sample_schema_yaml):
        client = self._setup_schema(validator, sample_schema_yaml)
        valid_df, invalid_df = validator.validate_dataframe(
            sample_dataframe, "test_table",
            storage_client=client, schema_bucket="schemas"
        )
        assert len(valid_df) == 3
        assert len(invalid_df) == 0

    def test_invalid_dataframe_returns_invalid_records(self, validator, sample_schema_yaml):
        client = self._setup_schema(validator, sample_schema_yaml)
        df = pd.DataFrame({
            "id": ["not_an_int"],
            "name": ["Alice"],
            "value": [10.5]
        })
        valid_df, invalid_df = validator.validate_dataframe(
            df, "test_table",
            storage_client=client, schema_bucket="schemas"
        )
        assert len(invalid_df) > 0

    def test_missing_schema_quarantines_all(self, validator, sample_dataframe):
        client = MockStorageClient()
        valid_df, invalid_df = validator.validate_dataframe(
            sample_dataframe, "unknown_table",
            storage_client=client, schema_bucket="schemas"
        )
        assert len(valid_df) == 0
        assert len(invalid_df) == 3
        assert "quarantine_reason" in invalid_df.columns

    def test_schema_caching(self, validator, sample_dataframe, sample_schema_yaml):
        """Second call should use cached schema, not reload from GCS."""
        client = self._setup_schema(validator, sample_schema_yaml)

        # First call loads from GCS
        validator.validate_dataframe(
            sample_dataframe, "test_table",
            storage_client=client, schema_bucket="schemas"
        )
        assert "test_table" in validator.SCHEMA_REGISTRY

        # Second call should use cache (even with a different client)
        mock_client = MockStorageClient()
        valid_df, _ = validator.validate_dataframe(
            sample_dataframe, "test_table",
            storage_client=mock_client, schema_bucket="schemas"
        )
        assert len(valid_df) == 3

    def test_empty_dataframe(self, validator, sample_schema_yaml):
        client = self._setup_schema(validator, sample_schema_yaml)
        df = pd.DataFrame(columns=["id", "name", "value"])
        valid_df, invalid_df = validator.validate_dataframe(
            df, "test_table",
            storage_client=client, schema_bucket="schemas"
        )
        assert len(valid_df) == 0
        assert len(invalid_df) == 0
