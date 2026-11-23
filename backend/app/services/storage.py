"""Acces au stockage objet via l'API S3.

Le meme code fonctionne avec MinIO (local) et avec un stockage objet cloud compatible S3 :
seules les variables S3_ENDPOINT_URL, S3_REGION et les cles changent.
"""

import logging
from collections.abc import Iterator
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...

    def iter_object(self, key: str) -> Iterator[bytes]: ...

    def ping(self) -> bool: ...


class S3Storage:
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None,
        region: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},  # necessaire pour MinIO
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=3,
                read_timeout=10,
            ),
        )

    def ensure_bucket(self) -> None:
        """Cree le bucket s'il n'existe pas (utilise uniquement en local avec MinIO)."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except ClientError:
            pass
        try:
            self.client.create_bucket(Bucket=self.bucket)
        except ClientError:
            # Hors us-east-1, le protocole S3 exige la region dans la requete de creation.
            self.client.create_bucket(
                Bucket=self.bucket,
                CreateBucketConfiguration={"LocationConstraint": self.client.meta.region_name},
            )
        logger.info("bucket cree", extra={"event": "bucket_created", "bucket": self.bucket})

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def iter_object(self, key: str) -> Iterator[bytes]:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"]
        try:
            yield from body.iter_chunks(chunk_size=64 * 1024)
        finally:
            body.close()

    def ping(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:  # noqa: BLE001
            return False


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    return S3Storage(
        bucket=settings.s3_bucket_attachments,
        endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
    )
