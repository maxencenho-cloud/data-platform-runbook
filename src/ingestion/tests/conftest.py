"""Shared test fixtures for the ingestion service."""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path so we can import main and validator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch GCP clients BEFORE main.py is imported anywhere.
# storage.Client() and bigquery.Client() run at module level (line 49-50),
# so they must be mocked before the first `import main`.
_storage_patcher = patch("google.cloud.storage.Client", return_value=MagicMock())
_bq_patcher = patch("google.cloud.bigquery.Client", return_value=MagicMock())
_storage_patcher.start()
_bq_patcher.start()


@pytest.fixture
def sample_csv_content():
    return "id,name,value\n1,Alice,10.5\n2,Bob,20.3\n"


@pytest.fixture
def invalid_csv_content():
    return "id,name,value\n1,Alice,not_a_number\n2,Bob,20.3\n"


@pytest.fixture
def empty_csv_content():
    return "id,name,value\n"


@pytest.fixture
def sample_schema_yaml():
    return """fields:
  - name: id
    type: int
  - name: name
    type: str
  - name: value
    type: float
"""


@pytest.fixture
def sample_records():
    """Sample valid records as list of dicts (replaces DataFrame fixture)."""
    return [
        {"id": 1, "name": "Alice", "value": 10.5},
        {"id": 2, "name": "Bob", "value": 20.3},
        {"id": 3, "name": "Charlie", "value": 30.1},
    ]
