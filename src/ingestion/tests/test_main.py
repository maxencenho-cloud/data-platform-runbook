"""Unit tests for the ingestion service main module."""
import pytest
import json
import base64
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from tests.mocks import (
    MockStorageClient, MockBucket, MockBlob,
    MockBQClient
)


@pytest.fixture
def mock_env(monkeypatch):
    """Set required environment variables."""
    monkeypatch.setenv("PROJECT_ID", "test-project")
    monkeypatch.setenv("QUARANTINE_BUCKET", "test-quarantine")
    monkeypatch.setenv("PROCESSING_BUCKET", "test-processing")
    monkeypatch.setenv("BRONZE_DATASET", "bronze_dev")
    monkeypatch.setenv("SCHEMA_BUCKET", "test-schemas")
    monkeypatch.setenv("STAGING_BUCKET", "test-staging")
    monkeypatch.setenv("ARCHIVE_BUCKET", "test-archive")


def make_pubsub_payload(bucket: str, filename: str) -> dict:
    """Create a Pub/Sub push message payload."""
    data = json.dumps({"bucket": bucket, "name": filename})
    encoded = base64.b64encode(data.encode()).decode()
    return {
        "message": {
            "data": encoded,
            "messageId": "test-msg-001",
            "publishTime": "2026-05-18T10:00:00Z"
        },
        "subscription": "projects/test/subscriptions/test-sub"
    }


def make_pubsub_attributes_payload(bucket: str, filename: str) -> dict:
    """Create a Pub/Sub message using attributes (no data field)."""
    return {
        "message": {
            "attributes": {
                "bucketId": bucket,
                "objectId": filename
            },
            "messageId": "test-msg-002",
            "publishTime": "2026-05-18T10:00:00Z"
        },
        "subscription": "projects/test/subscriptions/test-sub"
    }


class TestPubSubEndpoint:
    """Tests for the /v1/pubsub/messages endpoint."""

    @pytest.mark.asyncio
    async def test_valid_message_triggers_processing(self, mock_env):
        with patch("main.storage_client") as mock_storage, \
             patch("main.bq_client") as mock_bq:

            # Setup: file exists in landing bucket
            csv_content = "id,name,value\n1,Alice,10.5\n"
            blob = MockBlob("example_raw_data/data.csv", content=csv_content)
            landing = MockBucket("test-landing", blobs={"example_raw_data/data.csv": blob})
            processing = MockBucket("test-processing")
            staging = MockBucket("test-staging")
            archive = MockBucket("test-archive")
            quarantine = MockBucket("test-quarantine")
            schema_blob = MockBlob("bronze/example_raw_data.yaml",
                                   content="fields:\n  - name: id\n    type: int\n  - name: name\n    type: str\n  - name: value\n    type: float\n")
            schemas = MockBucket("test-schemas", blobs={"bronze/example_raw_data.yaml": schema_blob})

            def bucket_router(name):
                return {
                    "test-landing": landing,
                    "test-processing": processing,
                    "test-staging": staging,
                    "test-archive": archive,
                    "test-quarantine": quarantine,
                    "test-schemas": schemas,
                }.get(name, MockBucket(name))

            mock_storage.bucket = bucket_router
            mock_bq.load_table_from_uri.return_value = MagicMock(result=lambda **kwargs: None, errors=None)

            import importlib
            import main
            importlib.reload(main)
            main.storage_client = mock_storage
            main.bq_client = mock_bq

            transport = ASGITransport(app=main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = make_pubsub_payload("test-landing", "example_raw_data/data.csv")
                response = await client.post("/v1/pubsub/messages", json=payload)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_bucket_or_name_returns_400(self, mock_env):
        import importlib
        import main
        importlib.reload(main)

        transport = ASGITransport(app=main.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "message": {"data": base64.b64encode(b"{}").decode()},
                "subscription": "test-sub"
            }
            response = await client.post("/v1/pubsub/messages", json=payload)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_folder_creation_event_ignored(self, mock_env):
        import importlib
        import main
        importlib.reload(main)

        transport = ASGITransport(app=main.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = make_pubsub_payload("test-landing", "some_folder/")
            response = await client.post("/v1/pubsub/messages", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_attributes_based_message(self, mock_env):
        with patch("main.storage_client") as mock_storage, \
             patch("main.bq_client"):

            landing = MockBucket("test-landing")  # No file = already processed
            mock_storage.bucket = lambda name: landing

            import importlib
            import main
            importlib.reload(main)
            main.storage_client = mock_storage

            transport = ASGITransport(app=main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = make_pubsub_attributes_payload("test-landing", "test.csv")
                response = await client.post("/v1/pubsub/messages", json=payload)

            assert response.status_code == 200


class TestProcessFile:
    """Tests for the process_file function."""

    def test_file_not_found_returns_already_processed(self, mock_env):
        with patch("main.storage_client") as mock_storage:
            bucket = MockBucket("test-landing")  # Empty bucket = file not found
            mock_storage.bucket = lambda name: bucket

            import importlib
            import main
            importlib.reload(main)
            main.storage_client = mock_storage

            result = main.process_file("test-landing", "nonexistent.csv")
            assert result["status"] == "already_processed"

    def test_unsupported_format_quarantines(self, mock_env):
        with patch("main.storage_client") as mock_storage:
            blob = MockBlob("data.xml", content="<xml>not csv</xml>")
            landing = MockBucket("test-landing", blobs={"data.xml": blob})
            processing = MockBucket("test-processing")
            quarantine = MockBucket("test-quarantine")

            def bucket_router(name):
                return {
                    "test-landing": landing,
                    "test-processing": processing,
                    "test-quarantine": quarantine,
                }.get(name, MockBucket(name))

            mock_storage.bucket = bucket_router

            import importlib
            import main
            importlib.reload(main)
            main.storage_client = mock_storage

            result = main.process_file("test-landing", "data.xml")
            assert result["status"] == "quarantined"
