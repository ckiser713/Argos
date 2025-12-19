from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class StoredObject:
    uri: str
    bucket: Optional[str]
    key: Optional[str]
    checksum: str
    byte_size: int
    content_type: str


class StorageService:
    """Durable object storage abstraction for ingest uploads."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._s3_client = None

    def _client(self):
        if self.settings.storage_backend == "local":
            return None
        if self._s3_client:
            return self._s3_client

        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.settings.storage_endpoint_url,
            region_name=self.settings.storage_region,
            aws_access_key_id=self.settings.storage_access_key,
            aws_secret_access_key=self.settings.storage_secret_key,
            use_ssl=self.settings.storage_secure,
            config=Config(signature_version="s3v4"),
        )
        return self._s3_client

    def _ensure_bucket(self) -> None:
        client = self._client()
        if not client:
            return
        bucket = self.settings.storage_bucket
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            # 404/400/NoSuchBucket indicates missing bucket for S3/MinIO; attempt creation
            if str(error_code) in {"404", "400", "NoSuchBucket", "NotFound"}:
                create_args = {"Bucket": bucket}
                if self.settings.storage_region and not self.settings.storage_endpoint_url:
                    create_args["CreateBucketConfiguration"] = {
                        "LocationConstraint": self.settings.storage_region
                    }
                client.create_bucket(**create_args)
            else:
                raise

    def _normalize_content_type(self, content_type: Optional[str], filename: str) -> str:
        if content_type:
            return content_type.split(";")[0].strip().lower()
        guessed, _ = mimetypes.guess_type(filename)
        return (guessed or "application/octet-stream").lower()

    def _validate_content_type(self, content_type: str) -> None:
        allowed = set(self.settings.storage_allowed_types)
        if not allowed or {"*", "*/*"} & allowed:
            return
        base_type = content_type.split(";")[0].strip().lower()
        if base_type not in allowed:
            raise ValueError(f"Unsupported content type: {content_type}")

    def _validate_size(self, byte_size: int) -> None:
        limit_bytes = self.settings.storage_max_upload_mb * 1024 * 1024
        if byte_size > limit_bytes:
            raise ValueError(
                f"File too large ({byte_size} bytes). Max allowed is {self.settings.storage_max_upload_mb} MB."
            )

    def _compute_checksum(self, data: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(data)
        return digest.hexdigest()

    def save_bytes(
        self,
        *,
        project_id: str,
        filename: str,
        content_type: Optional[str],
        data: bytes,
    ) -> StoredObject:
        """Persist bytes to the configured storage backend."""
        byte_size = len(data)
        self._validate_size(byte_size)
        normalized_type = self._normalize_content_type(content_type, filename)
        self._validate_content_type(normalized_type)
        checksum = self._compute_checksum(data)

        key = f"{self.settings.storage_prefix.strip('/')}/{project_id}/{uuid.uuid4()}-{Path(filename).name}"

        if self.settings.storage_backend == "local":
            base = Path(self.settings.storage_local_dir).expanduser()
            dest = base / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            uri = dest.resolve().as_uri()
            logger.info("Stored ingest upload locally at %s", uri)
            return StoredObject(
                uri=uri,
                bucket=None,
                key=None,
                checksum=checksum,
                byte_size=byte_size,
                content_type=normalized_type,
            )

        client = self._client()
        self._ensure_bucket()
        client.put_object(
            Bucket=self.settings.storage_bucket,
            Key=key,
            Body=data,
            ContentType=normalized_type,
            Metadata={"checksum_sha256": checksum},
        )
        uri = f"s3://{self.settings.storage_bucket}/{key}"
        logger.info("Stored ingest upload in bucket %s with key %s", self.settings.storage_bucket, key)
        return StoredObject(
            uri=uri,
            bucket=self.settings.storage_bucket,
            key=key,
            checksum=checksum,
            byte_size=byte_size,
            content_type=normalized_type,
        )

    def download_to_path(self, uri: str) -> Path:
        """Download an object to a temporary path and return the path."""
        parsed = urlparse(uri)
        if parsed.scheme in {"file", ""}:
            local_path = Path(parsed.path if parsed.scheme else uri)
            if not local_path.exists():
                raise FileNotFoundError(f"Source not found at {local_path}")
            return local_path

        if parsed.scheme != "s3":
            raise ValueError(f"Unsupported URI scheme for ingest download: {uri}")

        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        client = self._client()
        if not client:
            raise RuntimeError("S3 client not configured")

        temp_dir = Path(tempfile.mkdtemp(prefix="ingest_"))
        dest = temp_dir / Path(key).name
        try:
            client.download_file(bucket, key, str(dest))
            return dest
        except Exception as exc:
            logger.error("Failed to download %s: %s", uri, exc)
            raise


storage_service = StorageService()

