import io
from datetime import datetime, timezone


class MockBlob:
    """Mock GCS Blob with generation tracking and file content."""

    def __init__(self, name, content=None, exists=True, generation=1, updated=None, bucket=None):
        self.name = name
        self._content = content or ""
        self._exists = exists
        self.generation = generation
        self.updated = updated or datetime.now(timezone.utc)
        self.bucket = bucket
        self.size = len(self._content)

    def reload(self):
        self.size = len(self._content)

    def exists(self):
        return self._exists

    def open(self, mode="rt"):
        return io.StringIO(self._content)

    def delete(self, if_generation_match=None):
        if self.bucket and self.name in self.bucket._blobs:
            del self.bucket._blobs[self.name]
        self._exists = False

    def download_as_text(self):
        return self._content

    def upload_from_string(self, data, content_type=None):
        self._content = data
        self.size = len(data)
        self._exists = True
        if self.bucket:
            self.bucket._blobs[self.name] = self


class MockBucket:
    """Mock GCS Bucket with blob storage and copy operations."""

    def __init__(self, name, blobs=None):
        self.name = name
        self._blobs = blobs or {}
        # Ensure initial blobs have their bucket reference set
        for b in self._blobs.values():
            b.bucket = self

    def get_blob(self, name):
        return self._blobs.get(name)

    def blob(self, name):
        if name in self._blobs:
            return self._blobs[name]
        return MockBlob(name, exists=False, bucket=self)

    def copy_blob(self, blob, destination_bucket, new_name=None,
                  if_source_generation_match=None, if_generation_match=None):
        new_blob = MockBlob(new_name or blob.name, blob._content, generation=blob.generation, bucket=destination_bucket)
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

    def result(self, timeout=None):
        if self._should_fail:
            raise Exception("BQ Load failed")


class MockBQClient:
    """Mock google.cloud.bigquery.Client."""

    def __init__(self, should_fail=False):
        self._should_fail = should_fail

    def load_table_from_uri(self, uri, table_id, job_config=None, job_id=None):
        return MockBQJob(should_fail=self._should_fail)
