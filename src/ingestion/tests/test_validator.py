"""Unit tests for the validator module."""
import pytest
import sys
import importlib
from tests.mocks import MockStorageClient, MockBucket, MockBlob


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
        result = validator.load_schema_from_gcs(MockStorageClient(), None, "test_table")
        assert result is None

    def test_returns_none_when_blob_not_found(self, validator):
        client = MockStorageClient()
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


class TestGetSchema:
    """Tests for lazy schema loading."""

    def test_caches_schema_on_first_load(self, validator, sample_schema_yaml):
        blob = MockBlob("bronze/test_table.yaml", content=sample_schema_yaml)
        bucket = MockBucket("schemas", blobs={"bronze/test_table.yaml": blob})
        client = MockStorageClient(buckets={"schemas": bucket})

        schema1 = validator.get_schema("test_table", client, "schemas")
        assert schema1 is not None
        assert "test_table" in validator.SCHEMA_REGISTRY

        # Second call uses cache (different client, no GCS access)
        schema2 = validator.get_schema("test_table", MockStorageClient(), "schemas")
        assert schema2 is schema1

    def test_returns_none_for_unknown_table(self, validator):
        schema = validator.get_schema("unknown", MockStorageClient(), "schemas")
        assert schema is None


class TestValidateRecord:
    """Tests for single-record validation."""

    def _get_schema(self, validator, sample_schema_yaml):
        blob = MockBlob("bronze/test_table.yaml", content=sample_schema_yaml)
        bucket = MockBucket("schemas", blobs={"bronze/test_table.yaml": blob})
        client = MockStorageClient(buckets={"schemas": bucket})
        return validator.get_schema("test_table", client, "schemas")

    def test_valid_record_returns_none(self, validator, sample_schema_yaml):
        schema = self._get_schema(validator, sample_schema_yaml)
        error = validator.validate_record({"id": 1, "name": "Alice", "value": 10.5}, schema)
        assert error is None

    def test_valid_csv_string_record(self, validator, sample_schema_yaml):
        """CSV records are all strings — Pydantic should coerce '1' to int."""
        schema = self._get_schema(validator, sample_schema_yaml)
        error = validator.validate_record({"id": "1", "name": "Alice", "value": "10.5"}, schema)
        assert error is None

    def test_invalid_record_returns_error(self, validator, sample_schema_yaml):
        schema = self._get_schema(validator, sample_schema_yaml)
        error = validator.validate_record({"id": "not_int", "name": "Alice", "value": 10.5}, schema)
        assert error is not None

    def test_empty_string_treated_as_none(self, validator, sample_schema_yaml):
        """Empty CSV cells should be treated as None for nullable fields."""
        # Add a nullable field schema
        nullable_schema_yaml = """fields:
  - name: id
    type: int
  - name: name
    type: str
  - name: value
    type: float
    nullable: true
"""
        blob = MockBlob("bronze/nullable_test.yaml", content=nullable_schema_yaml)
        bucket = MockBucket("schemas", blobs={"bronze/nullable_test.yaml": blob})
        client = MockStorageClient(buckets={"schemas": bucket})
        schema = validator.get_schema("nullable_test", client, "schemas")

        error = validator.validate_record({"id": "1", "name": "Alice", "value": ""}, schema)
        assert error is None  # Empty string → None → valid for nullable field
