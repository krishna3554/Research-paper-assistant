
from uuid import uuid4
from config import get_settings
import boto3
from botocore.client import Config
from pathlib import Path

settings = get_settings()
STORAGE_PROVIDER = settings.storage_provider
S3_ENDPOINT_URL = settings.s3_endpoint_url
S3_BUCKET_NAME = settings.s3_bucket_name
S3_ACCESS_KEY_ID = settings.s3_access_key_id
S3_SECRET_ACCESS_KEY = settings.s3_secret_access_key
S3_REGION = settings.s3_region  

def get_storage_client():
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME is not set")
    
    if not settings.s3_access_key_id or not settings.s3_secret_access_key:
        raise RuntimeError("S3 credentials not set")

    client_kwargs = {
        "service_name": "s3",
        "aws_access_key_id": settings.s3_access_key_id,
        "aws_secret_access_key": settings.s3_secret_access_key,
        "region_name": settings.s3_region,
        "config": Config(signature_version="s3v4")
    }

    if S3_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url

    return boto3.client(**client_kwargs)

def build_paper_storage_key(filename: str) -> str:
    unique_id = uuid4().hex
    safe_filename = filename.replace("/","_").replace("\\", "_")
    return f"papers/{unique_id}/{safe_filename}"


def upload_pdf_to_storage(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> str:
    storage_key = build_paper_storage_key(filename)
    client = get_storage_client()

    client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=storage_key,
        Body=file_bytes,
        ContentType=content_type,
    )

    return storage_key

def download_file_from_storage(storage_key: str, destination: Path) -> None:
    client = get_storage_client()
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    client.download_file(
        Bucket=S3_BUCKET_NAME,
        Key=storage_key,
        Filename=str(destination),
    )
