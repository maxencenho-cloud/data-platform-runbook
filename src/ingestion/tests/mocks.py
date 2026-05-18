"""Mock classes for GCS and BigQuery clients used in tests."""
import io


class MockBlob:
    """Mock GCS Blob with generation tracking and file content."""

    def __init__(self, name, content=None, exists=True, generation=1):
        self.name = name
        self._content = content or ""
        self._exists = exists
        self.generation = generation

    def exists(self):
        return self._exists

    def open(self, mode="rt"):
        return io.StringIO(self._content)

    def delete(self, if_generation_match=None):
        pass

    def download_as_text(self):
        return self._content


class MockBucket:
    """Mock GCS Bucket with blob storage and copy operations."""

    def __init__(self, name, blobs=None):
        self.name = name
        self._blobs = blobs or {}

    def get_blob(self, name):
        return self._blobs.get(name)

    def blob(self, name):
        return self._blobs.get(name, MockBlob(name, exists=False))

    def copy_blob(self, blob, destination_bucket, new_name=None,
                  if_source_generation_match=None, if_generation_match=None):
        new_blob = MockBlob(new_name or blob.name, blob._content, generation=blob.generation)
        destination_bucket._blobs[new_blob.name] = new_blob
        return new_blob


class MockStorageClient:
    """Mock google.cloud.storage.Client."""

    def __init__(self, buckets=None):
        self._buckets = buckets or {}

    def bucket(self, name):
        if name not in self._buckets:
            self._buckets[name] = MockBucket(name)
        return self._buckets[name]


class MockBQJob:
    """Mock BigQuery Load Job."""

    def __init__(self, should_fail=False, errors=None):
        self._should_fail = should_fail
        self.errors = errors

    def result(self):
        if self._should_fail:
            raise Exception("BQ Load failed")


class MockBQClient:
    """Mock google.cloud.bigquery.Client."""

    def __init__(self, should_fail=False):
        self._should_fail = should_fail

    def load_table_from_uri(self, uri, table_id, job_config=None, job_id=None):
        return MockBQJob(should_fail=self._should_fail)
