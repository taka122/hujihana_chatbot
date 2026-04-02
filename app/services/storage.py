from __future__ import annotations

import logging
from urllib.parse import urlparse

from botocore.client import Config
from botocore.exceptions import ClientError

import boto3

from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.s3_bucket
        self._presign_expire_sec = settings.s3_presign_expire_sec
        self._client = self._build_client(
            endpoint_url=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )
        self._presign_client = self._client

        public_endpoint = settings.s3_public_endpoint
        if public_endpoint:
            parsed = urlparse(public_endpoint)
            if parsed.scheme and parsed.netloc:
                # Presigned URL must be generated with the same host users access.
                self._presign_client = self._build_client(
                    endpoint_url=public_endpoint,
                    access_key=settings.s3_access_key,
                    secret_key=settings.s3_secret_key,
                    region=settings.s3_region,
                )
            else:
                logger.warning("Invalid S3_PUBLIC_ENDPOINT value: %s", public_endpoint)

    def _build_client(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str,
    ):
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            logger.info("Creating bucket %s", self._bucket)
            self._client.create_bucket(Bucket=self._bucket)

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> None:
        if key.startswith("drive://"):
            logger.info("Skipping S3 upload for Drive-sourced file: %s", key)
            return
        self.ensure_bucket()
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def download_bytes(self, key: str) -> bytes:
        if key.startswith("drive://"):
            # Note: In a production app, we'd use the DriveService here.
            # For simplicity, we'll assume the caller (ingest job) handles Drive files specially
            # or we implement a fallback if needed.
            raise RuntimeError("Direct download_bytes from drive:// not implemented in StorageService yet. Use DriveService directly.")
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def generate_presigned_get_url(self, key: str) -> str:
        if key.startswith("drive://"):
            # Return the direct webViewLink (which we'll store in Document if needed, 
            # or just return the drive URL base)
            drive_id = key.replace("drive://", "")
            return f"https://drive.google.com/file/d/{drive_id}/view"
        return self._presign_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=self._presign_expire_sec,
        )

    def delete_object(self, key: str) -> None:
        if key.startswith("drive://"):
            logger.info("Skipping S3 delete for Drive-sourced file: %s", key)
            return
        self._client.delete_object(Bucket=self._bucket, Key=key)
