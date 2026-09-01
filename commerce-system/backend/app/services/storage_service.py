"""
Storage abstraction over S3 / Cloudflare R2 (Section 21).

Both are S3-compatible, so one boto3 client works for either — R2 just
needs STORAGE_ENDPOINT_URL set to the account's R2 endpoint. Nothing else
in the codebase should import boto3 directly; go through this module so
swapping providers stays a one-file change.
"""
import io

import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()


def _client():
    kwargs = {
        "region_name": settings.STORAGE_REGION,
        "config": Config(signature_version="s3v4"),
    }
    if settings.STORAGE_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.STORAGE_ENDPOINT_URL
    if settings.STORAGE_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.STORAGE_ACCESS_KEY_ID
    if settings.STORAGE_SECRET_ACCESS_KEY:
        kwargs["aws_secret_access_key"] = settings.STORAGE_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


def upload_bytes(*, key: str, data: bytes, content_type: str) -> None:
    client = _client()
    client.upload_fileobj(
        io.BytesIO(data),
        settings.STORAGE_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def generate_presigned_download_url(*, key: str, expires_in_seconds: int = 300) -> str:
    """
    Short-lived signed URL so customers can download their own invoice
    without the object being publicly readable (Section 21-22).
    """
    client = _client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.STORAGE_BUCKET, "Key": key},
        ExpiresIn=expires_in_seconds,
    )
