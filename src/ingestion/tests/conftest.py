"""Shared test fixtures for the ingestion service."""
import pytest
import pandas as pd
import sys
import os

# Add parent directory to path so we can import main and validator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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
def sample_dataframe():
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "value": [10.5, 20.3, 30.1]
    })


@pytest.fixture
def invalid_dataframe():
    return pd.DataFrame({
        "id": ["not_int", 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "value": [10.5, "not_float", 30.1]
    })
